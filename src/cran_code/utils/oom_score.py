"""Linux OOM killer score adjustment, best-effort.

The production host is memory-constrained. When the kernel OOM killer fires it
picks the process with the highest badness score, which is derived from RSS
plus ``/proc/<pid>/oom_score_adj``. Without adjustment the biggest process —
usually the web server or a session worker — gets killed, which drops every
WebSocket connection and orphans background tasks (they are later reported as
"lost" because their heartbeat stops).

We bias the scores so the kernel sacrifices replaceable work first:

- web server main process: strongly protected (``OOM_SCORE_SERVER``)
- per-session worker processes: mildly protected (``OOM_SCORE_SESSION_WORKER``)
- background task workers (builds, test runs, ...): strongly preferred victims
  (``OOM_SCORE_BACKGROUND_WORKER``); their children inherit the score

All of this is best-effort: on non-Linux platforms or without write permission
the helpers silently no-op.
"""

from __future__ import annotations

import os

from cran_code.utils.logging import logger

OOM_SCORE_SERVER = -800
OOM_SCORE_SESSION_WORKER = -300
OOM_SCORE_BACKGROUND_WORKER = 800

_PROC_OOM_SCORE_ADJ = "/proc/self/oom_score_adj"


def set_oom_score_adj(value: int, *, _path: str = _PROC_OOM_SCORE_ADJ) -> bool:
    """Set ``oom_score_adj`` for the current process. Returns True on success.

    Values are clamped to the kernel range [-1000, 1000]. Never raises.
    """
    if os.name != "posix":
        return False
    value = max(-1000, min(1000, int(value)))
    try:
        # r+ so a missing path (non-Linux /proc) fails instead of being created.
        with open(_path, "r+") as f:
            f.write(str(value))
    except OSError as exc:
        logger.debug("set_oom_score_adj({value}) failed: {exc}", value=value, exc=exc)
        return False
    logger.debug("set_oom_score_adj({value}) applied", value=value)
    return True
