Create and start a goal for this session. Goal mode turns the session into an autonomous multi-turn loop: after each turn, the driver automatically continues working toward the goal until it is completed, blocked, paused, or a budget is exhausted.

## When to Use
Only use this tool when the user explicitly asks for an autonomous, multi-turn effort with a clear end state (e.g. "keep refactoring until the test suite passes"). For ordinary one-shot requests, do NOT create a goal.

## How It Works
- The goal persists in the session and survives compaction; the full goal context is re-injected at every turn boundary.
- At most ONE goal can exist per session. If a goal already exists, this tool fails — ask the user whether to cancel/replace it first.
- After the goal is created, `UpdateGoal` and `SetGoalBudget` become available.
- The user is asked to approve goal creation unless yolo/afk auto-approval is active.

## Budgets
Only set `max_turns` / `max_tokens` / `max_seconds` when the user states explicit hard limits. Otherwise leave them unset; a default turn cap still applies as a safety net.
