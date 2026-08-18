from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, NamedTuple, Protocol, runtime_checkable

import kosong
from kosong.chat_provider import TokenUsage
from kosong.message import Message
from kosong.tooling.empty import EmptyToolset

import cran_code.prompts as prompts
from cran_code.llm import LLM
from cran_code.soul.message import system
from cran_code.utils.logging import logger
from cran_code.wire.types import ContentPart, TextPart, ThinkPart

COMPACTION_SYSTEM_PROMPT = "You are a helpful assistant that compacts conversation context."
# Prepended (as a system-tagged part) before the compaction summary. Teaches
# the model to treat the summary as fallible notes, not proof.
COMPACTION_OUTPUT_PREFIX = (
    "The conversation so far has been compacted to free up context. What follows "
    "is your own working summary of this task — use it to continue your train of "
    "thought rather than starting over. Treat it as notes, not proof: where it "
    "says a step was done, tests passed, or a fix worked, verify that yourself "
    "before relying on it. Any user messages earlier in this context are preserved "
    "verbatim from the compacted conversation; where a system-reminder note among "
    "them marks an omitted middle section, the user messages it replaced are "
    "covered by this summary."
)


class CompactionResult(NamedTuple):
    messages: Sequence[Message]
    usage: TokenUsage | None
    trace_id: str | None = None

    @property
    def estimated_token_count(self) -> int:
        """Estimate the token count of the compacted messages.

        When LLM usage is available, ``usage.output`` gives the exact token count
        of the generated summary (the first message).  Preserved messages (all
        subsequent messages) are estimated from their text length.

        When usage is not available (no compaction LLM call was made), all
        messages are estimated from text length.

        The estimate is intentionally conservative — it will be replaced by the
        real value on the next LLM call.
        """
        if self.usage is not None and len(self.messages) > 0:
            summary_tokens = self.usage.output
            preserved_tokens = estimate_text_tokens(self.messages[1:])
            return summary_tokens + preserved_tokens

        return estimate_text_tokens(self.messages)


def estimate_text_tokens(messages: Sequence[Message]) -> int:
    """Estimate tokens from message text content using a character-based heuristic."""
    total_chars = 0
    for msg in messages:
        for part in msg.content:
            if isinstance(part, TextPart):
                total_chars += len(part.text)
    # ~4 chars per token for English; somewhat underestimates for CJK text,
    # but this is a temporary estimate that gets corrected on the next LLM call.
    return total_chars // 4


def should_auto_compact(
    token_count: int,
    max_context_size: int,
    *,
    trigger_ratio: float,
    reserved_context_size: int,
) -> bool:
    """Determine whether auto-compaction should be triggered.

    Returns True when either condition is met (whichever fires first):
    - Ratio-based: token_count >= max_context_size * trigger_ratio
    - Reserved-based: token_count + reserved_context_size >= max_context_size
    """
    return (
        token_count >= max_context_size * trigger_ratio
        or token_count + reserved_context_size >= max_context_size
    )


@runtime_checkable
class Compaction(Protocol):
    async def compact(
        self,
        messages: Sequence[Message],
        llm: LLM,
        *,
        custom_instruction: str = "",
    ) -> CompactionResult:
        """
        Compact a sequence of messages into a new sequence of messages.

        Args:
            messages (Sequence[Message]): The messages to compact.
            llm (LLM): The LLM to use for compaction.
            custom_instruction: Optional user instruction to guide compaction focus.
        Returns:
            CompactionResult: The compacted messages and token usage from the compaction LLM call.

        Raises:
            ChatProviderError: When the chat provider returns an error.
        """
        ...


if TYPE_CHECKING:

    def type_check(simple: SimpleCompaction):
        _: Compaction = simple


class SimpleCompaction:
    def __init__(
        self, max_preserved_messages: int = 2, max_preserved_tokens: int | None = None
    ) -> None:
        self.max_preserved_messages = max_preserved_messages
        self.max_preserved_tokens = max_preserved_tokens

    async def compact(
        self,
        messages: Sequence[Message],
        llm: LLM,
        *,
        custom_instruction: str = "",
    ) -> CompactionResult:
        compact_message, to_preserve = self.prepare(messages, custom_instruction=custom_instruction)
        if compact_message is None:
            return CompactionResult(messages=to_preserve, usage=None)

        logger.debug("Compacting context...")
        result = await kosong.step(
            chat_provider=llm.chat_provider,
            system_prompt=COMPACTION_SYSTEM_PROMPT,
            toolset=EmptyToolset(),
            history=[compact_message],
        )
        if result.usage:
            logger.debug(
                "Compaction used {input} input tokens and {output} output tokens",
                input=result.usage.input,
                output=result.usage.output,
            )

        content: list[ContentPart] = [system(COMPACTION_OUTPUT_PREFIX)]
        compacted_msg = result.message

        # drop thinking parts if any
        content.extend(part for part in compacted_msg.content if not isinstance(part, ThinkPart))
        compacted_messages: list[Message] = [Message(role="user", content=content)]
        compacted_messages.extend(to_preserve)
        return CompactionResult(
            messages=compacted_messages, usage=result.usage, trace_id=result.trace_id
        )

    class PrepareResult(NamedTuple):
        compact_message: Message | None
        to_preserve: Sequence[Message]

    def prepare(
        self, messages: Sequence[Message], *, custom_instruction: str = ""
    ) -> PrepareResult:
        if not messages or self.max_preserved_messages <= 0:
            return self.PrepareResult(compact_message=None, to_preserve=messages)

        history = list(messages)
        preserve_start_index = len(history)
        n_preserved = 0
        preserved_tokens = 0
        budget_limited = False
        for index in range(len(history) - 1, -1, -1):
            msg = history[index]
            if msg.role not in {"user", "assistant"}:
                continue

            msg_tokens = estimate_text_tokens([msg])
            if (
                self.max_preserved_tokens is not None
                and preserved_tokens + msg_tokens > self.max_preserved_tokens
            ):
                budget_limited = True
                break

            preserved_tokens += msg_tokens
            n_preserved += 1
            preserve_start_index = index
            if n_preserved == self.max_preserved_messages:
                break

        if n_preserved == 0:
            # The most recent user/assistant messages are too large to preserve.
            # Compact the entire history and keep nothing from before compaction.
            preserve_start_index = len(history)
            to_compact = history
            to_preserve: Sequence[Message] = []
        elif n_preserved < self.max_preserved_messages and not budget_limited:
            # Not enough user/assistant messages to fill the count cap.
            return self.PrepareResult(compact_message=None, to_preserve=messages)
        else:
            to_compact = history[:preserve_start_index]
            to_preserve = history[preserve_start_index:]

        if not to_compact:
            # Nothing older to summarize; preserving the tail is the best we can do.
            return self.PrepareResult(compact_message=None, to_preserve=to_preserve)

        # Create input message for compaction
        compact_message = Message(role="user", content=[])
        for i, msg in enumerate(to_compact):
            compact_message.content.append(
                TextPart(text=f"## Message {i + 1}\nRole: {msg.role}\nContent:\n")
            )
            compact_message.content.extend(
                part for part in msg.content if isinstance(part, TextPart)
            )
        prompt_text = "\n" + prompts.COMPACT
        if custom_instruction:
            prompt_text += (
                "\n\n**User's Custom Compaction Instruction:**\n"
                "The user has specifically requested the following focus during compaction. "
                "You MUST prioritize this instruction above the default compression priorities:\n"
                f"{custom_instruction}"
            )
        compact_message.content.append(TextPart(text=prompt_text))
        return self.PrepareResult(compact_message=compact_message, to_preserve=to_preserve)
