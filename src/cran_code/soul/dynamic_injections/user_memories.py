"""Session-start injection of the user's cross-session memories (ADR 002).

Registered from `KimiCLI.create` for root sessions whose owner is a signed-in
user. The brief is fetched lazily on the first LLM step (the provider's
``get_injections`` is async, so the DB read does not block session startup),
injected once as a ``<user-memories>`` block, and re-injected after compaction
(which may have collapsed the original block away). Memory content refreshes
on the next session load — that is deliberate for v1.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from kosong.message import Message

from cran_code.soul.dynamic_injection import DynamicInjection, DynamicInjectionProvider

if TYPE_CHECKING:
    from cran_code.soul.kimisoul import KimiSoul

USER_MEMORIES_INJECTION_TYPE = "user_memories"


class UserMemoriesInjectionProvider(DynamicInjectionProvider):
    """Injects the user's top memories once per session (and after compaction)."""

    def __init__(self, user_id: str, project_id: str | None = None) -> None:
        self._user_id = user_id
        self._project_id = project_id
        self._brief: str | None = None  # None = not fetched yet; "" = nothing to inject
        self._injected = False

    async def get_injections(
        self,
        history: Sequence[Message],
        soul: KimiSoul,
    ) -> list[DynamicInjection]:
        _ = history
        if soul.is_subagent or self._injected:
            return []
        self._injected = True
        if self._brief is None:
            from cran_code.web.db.memories import build_brief

            self._brief = await build_brief(self._user_id, project_id=self._project_id)
        if not self._brief:
            return []
        return [DynamicInjection(type=USER_MEMORIES_INJECTION_TYPE, content=self._brief)]

    async def on_context_compacted(self) -> None:
        # Compaction rebuilds history; the original memories block may have been
        # summarized away, so re-inject the cached brief on the next step.
        self._injected = False
