Update the status of the current session goal.

## Statuses
- `complete`: the goal is fully achieved (completion criteria met). The goal record is cleared by the runtime. After calling with this status, write a brief final summary for the user: what was achieved, key changes, and anything left outstanding. Do not start new work afterwards.
- `blocked`: the goal cannot be advanced without external input or a user decision. Always provide `reason`. After calling, briefly tell the user why you are blocked and what you need.
- `paused`: park the goal (e.g. the user asked to pause). It will not be advanced autonomously until resumed.
- `active`: resume a paused/blocked goal. Only use when the user explicitly asks to resume.

## Discipline
- Do NOT call with `complete` unless the goal is genuinely done; unfinished work must continue in the next turn instead.
- Do NOT call with `blocked` for mere uncertainty; break the remaining work into smaller steps.
