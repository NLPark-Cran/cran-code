"""Cross-session memory tools: RememberMemory / SearchMemory / ForgetMemory (root agent only).

Part of companion-mode memory (ADR 002). Memories are stored per user in the
platform database and follow the user across sessions; see
`cran_code.web.db.memories` for the store layer.
"""

# NOTE: no `from __future__ import annotations` here — KimiToolset dependency
# injection inspects raw constructor annotations, which must stay real types.

from pathlib import Path
from typing import Literal, override

from kosong.tooling import CallableTool2, ToolError, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field

from cran_code.soul.agent import Runtime
from cran_code.tools.utils import load_desc
from cran_code.web.db import memories as memory_store

ANONYMOUS_OWNER_IDS = ("v1_anonymous", "local")


def _root_only_error() -> ToolError:
    return ToolError(
        message="Memory tools are only available to the main agent.",
        brief="Memory unavailable",
    )


def _require_owner(runtime: Runtime) -> str | ToolError:
    """Resolve the session owner's user id, or a friendly error for anonymous sessions."""
    owner_id = runtime.session.state.owner_id
    if not owner_id or owner_id in ANONYMOUS_OWNER_IDS:
        return ToolError(
            message=(
                "Cross-session memory requires a signed-in account; this session is "
                "anonymous, so nothing can be remembered across sessions. Session-local "
                "notes can still go into files or the todo list."
            ),
            brief="Memory needs an account",
        )
    return owner_id


class RememberMemoryParams(BaseModel):
    kind: Literal["fact", "preference", "decision", "gotcha"] = Field(
        description=(
            "fact: stable knowledge about the user or their environment; "
            "preference: how the user likes things done; "
            "decision: a choice made with lasting rationale; "
            "gotcha: a pitfall / non-obvious trap worth not re-hitting."
        ),
    )
    content: str = Field(
        description=(
            "The durable fact to remember, one or two sentences, self-contained. "
            "NEVER include secrets, tokens, passwords, or credentials."
        ),
        min_length=1,
        max_length=memory_store.MAX_MEMORY_CONTENT_LENGTH,
    )
    evidence: str | None = Field(
        default=None,
        description="Optional short pointer to where this was learned (quote or file).",
        max_length=memory_store.MAX_MEMORY_EVIDENCE_LENGTH,
    )
    salience: float | None = Field(
        default=None,
        ge=memory_store.MIN_SALIENCE,
        le=memory_store.MAX_SALIENCE,
        description="Importance 0.1-10 (default 1.0). Higher = surfaced more prominently.",
    )


class RememberMemory(CallableTool2[RememberMemoryParams]):
    name: str = "RememberMemory"
    description: str = load_desc(Path(__file__).parent / "remember_memory.md")
    params: type[RememberMemoryParams] = RememberMemoryParams

    def __init__(self, runtime: Runtime) -> None:
        super().__init__()
        self._runtime = runtime

    @override
    async def __call__(self, params: RememberMemoryParams) -> ToolReturnValue:
        if self._runtime.role != "root":
            return _root_only_error()
        owner = _require_owner(self._runtime)
        if isinstance(owner, ToolError):
            return owner

        try:
            result = await memory_store.remember(
                user_id=owner,
                kind=params.kind,
                content=params.content,
                evidence=params.evidence,
                salience=params.salience if params.salience is not None else 1.0,
                source_session_id=self._runtime.session.id,
            )
        except memory_store.SecretRejectedError as exc:
            return ToolError(message=str(exc), brief="Secret rejected")
        except memory_store.InvalidKindError as exc:
            return ToolError(message=str(exc), brief="Invalid kind")

        memory = result.memory
        if result.created:
            return ToolOk(
                output=f"Memory saved (id={memory.id}, kind={memory.kind}): {memory.content}",
                message="Memory saved",
                brief="Memory saved",
            )
        return ToolOk(
            output=(
                f"Updated existing memory (id={memory.id}, salience now "
                f"{memory.salience:.1f}) instead of creating a duplicate: {memory.content}"
            ),
            message="Memory updated",
            brief="Memory updated",
        )


class SearchMemoryParams(BaseModel):
    query: str = Field(
        description="Substring to look for in remembered content (case-insensitive).",
        min_length=1,
        max_length=200,
    )
    limit: int = Field(default=10, ge=1, le=50, description="Max results (default 10).")


class SearchMemory(CallableTool2[SearchMemoryParams]):
    name: str = "SearchMemory"
    description: str = load_desc(Path(__file__).parent / "search_memory.md")
    params: type[SearchMemoryParams] = SearchMemoryParams

    def __init__(self, runtime: Runtime) -> None:
        super().__init__()
        self._runtime = runtime

    @override
    async def __call__(self, params: SearchMemoryParams) -> ToolReturnValue:
        if self._runtime.role != "root":
            return _root_only_error()
        owner = _require_owner(self._runtime)
        if isinstance(owner, ToolError):
            return owner

        memories = await memory_store.search(owner, params.query, limit=params.limit)
        if not memories:
            return ToolOk(
                output=f"No memories match {params.query!r}.",
                message="No memories found",
            )
        lines = [
            f"- [{m.kind}] {m.content}  (id={m.id}, salience={m.salience:.1f})"
            for m in memories
        ]
        return ToolOk(
            output=f"Memories matching {params.query!r} (best first):\n" + "\n".join(lines),
            message=f"{len(memories)} memories found",
            brief=f"{len(memories)} memories",
        )


class ForgetMemoryParams(BaseModel):
    id: str = Field(
        description="The id of the memory to forget (from SearchMemory output).",
        min_length=1,
    )


class ForgetMemory(CallableTool2[ForgetMemoryParams]):
    name: str = "ForgetMemory"
    description: str = load_desc(Path(__file__).parent / "forget_memory.md")
    params: type[ForgetMemoryParams] = ForgetMemoryParams

    def __init__(self, runtime: Runtime) -> None:
        super().__init__()
        self._runtime = runtime

    @override
    async def __call__(self, params: ForgetMemoryParams) -> ToolReturnValue:
        if self._runtime.role != "root":
            return _root_only_error()
        owner = _require_owner(self._runtime)
        if isinstance(owner, ToolError):
            return owner

        memory = await memory_store.archive(owner, params.id)
        if memory is None:
            return ToolError(
                message="No active memory with that id belongs to this user.",
                brief="Memory not found",
            )
        return ToolOk(
            output=f"Forgot memory (id={memory.id}): {memory.content}",
            message="Memory forgotten",
            brief="Memory forgotten",
        )
