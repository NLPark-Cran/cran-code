"""Goal mode tools: CreateGoal / GetGoal / UpdateGoal / SetGoalBudget (root agent only)."""

# NOTE: no `from __future__ import annotations` here — KimiToolset dependency
# injection inspects raw constructor annotations, which must stay real types.

import json
from pathlib import Path
from typing import Literal, override

from kosong.tooling import CallableTool2, ToolError, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field, field_validator, model_validator

from cran_code.soul.agent import Runtime
from cran_code.soul.approval import Approval
from cran_code.soul.goal import (
    CREATE_GOAL_TOOL_NAME,
    GET_GOAL_TOOL_NAME,
    MAX_GOAL_OBJECTIVE_LENGTH,
    MAX_GOAL_SECONDS,
    MIN_GOAL_SECONDS,
    SET_GOAL_BUDGET_TOOL_NAME,
    UPDATE_GOAL_TOOL_NAME,
    GoalBudgets,
    GoalExistsError,
    GoalNotFoundError,
    GoalStore,
    GoalTransitionError,
    current_active_seconds,
    sync_goal_tool_visibility,
)
from cran_code.soul.toolset import KimiToolset
from cran_code.tools.utils import load_desc


def _goal_store(runtime: Runtime) -> GoalStore:
    return GoalStore(runtime.session.dir)


def _root_only_error() -> ToolError:
    return ToolError(
        message="Goal tools are only available to the main agent.",
        brief="Goal unavailable",
    )


class CreateGoalParams(BaseModel):
    objective: str = Field(
        description=(
            "The end state to achieve, in the user's words. "
            f"Non-empty, at most {MAX_GOAL_OBJECTIVE_LENGTH} characters."
        ),
        min_length=1,
        max_length=MAX_GOAL_OBJECTIVE_LENGTH,
    )
    criteria: str | None = Field(
        default=None,
        description="Optional machine-checkable completion criteria.",
        max_length=MAX_GOAL_OBJECTIVE_LENGTH,
    )
    max_turns: int | None = Field(default=None, gt=0, description="Hard turn limit.")
    max_tokens: int | None = Field(default=None, gt=0, description="Hard context-token limit.")
    max_seconds: int | None = Field(
        default=None,
        ge=MIN_GOAL_SECONDS,
        le=MAX_GOAL_SECONDS,
        description=f"Hard active-time limit in seconds ({MIN_GOAL_SECONDS}-{MAX_GOAL_SECONDS}).",
    )

    @field_validator("objective")
    @classmethod
    def objective_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("objective must not be blank")
        return v.strip()


class CreateGoal(CallableTool2[CreateGoalParams]):
    name: str = CREATE_GOAL_TOOL_NAME
    description: str = load_desc(Path(__file__).parent / "create_goal.md")
    params: type[CreateGoalParams] = CreateGoalParams

    def __init__(self, runtime: Runtime, toolset: KimiToolset, approval: Approval) -> None:
        super().__init__()
        self._runtime = runtime
        self._toolset = toolset
        self._approval = approval

    @override
    async def __call__(self, params: CreateGoalParams) -> ToolReturnValue:
        if self._runtime.role != "root":
            return _root_only_error()

        store = _goal_store(self._runtime)
        if store.load() is not None:
            return ToolError(
                message=(
                    "A goal already exists for this session. Ask the user whether to "
                    "cancel/replace it first; only one goal can be active at a time."
                ),
                brief="Goal already exists",
            )

        # Goal creation is user-visible and starts autonomous quota spend, so it
        # requires approval unless yolo/afk auto-approval is active.
        approval_result = await self._approval.request(
            self.name,
            "create goal",
            f"Start goal mode with objective: {params.objective}",
        )
        if not approval_result:
            return approval_result.rejection_error()

        budgets = GoalBudgets(
            max_turns=params.max_turns,
            max_tokens=params.max_tokens,
            max_seconds=params.max_seconds,
        )
        try:
            record = store.create(params.objective, criteria=params.criteria, budgets=budgets)
        except GoalExistsError:
            return ToolError(message="A goal already exists.", brief="Goal already exists")

        sync_goal_tool_visibility(self._toolset, has_goal=True)
        return ToolOk(
            output=(
                f'Goal created and active: "{record.objective}". The driver will '
                "automatically continue with new turns after this one until the goal is "
                "completed, blocked, paused, or a budget is exhausted. Work toward the goal "
                "now; call UpdateGoal when it is done or blocked."
            ),
            message="Goal created",
            brief="Goal created",
        )


class GetGoalParams(BaseModel):
    pass


class GetGoal(CallableTool2[GetGoalParams]):
    name: str = GET_GOAL_TOOL_NAME
    description: str = load_desc(Path(__file__).parent / "get_goal.md")
    params: type[GetGoalParams] = GetGoalParams

    def __init__(self, runtime: Runtime) -> None:
        super().__init__()
        self._runtime = runtime

    @override
    async def __call__(self, params: GetGoalParams) -> ToolReturnValue:
        if self._runtime.role != "root":
            return _root_only_error()

        record = _goal_store(self._runtime).load()
        if record is None:
            return ToolOk(output="No goal is set for this session.", message="No goal")

        snapshot = record.model_dump(mode="json")
        snapshot["stats"]["active_seconds"] = round(
            current_active_seconds(record, record.updated_at), 1
        )
        return ToolOk(
            output=f"Current goal:\n{json.dumps(snapshot, indent=2, ensure_ascii=False)}",
            message="Goal snapshot",
        )


class UpdateGoalParams(BaseModel):
    status: Literal["complete", "blocked", "paused", "active"] = Field(
        description=(
            "New status: complete (goal achieved, record cleared), blocked (needs external "
            "input), paused (park), active (resume from paused/blocked)."
        ),
    )
    reason: str | None = Field(
        default=None,
        description="Why the goal is being blocked/paused. Required for blocked.",
        max_length=1000,
    )


class UpdateGoal(CallableTool2[UpdateGoalParams]):
    name: str = UPDATE_GOAL_TOOL_NAME
    description: str = load_desc(Path(__file__).parent / "update_goal.md")
    params: type[UpdateGoalParams] = UpdateGoalParams

    def __init__(self, runtime: Runtime, toolset: KimiToolset) -> None:
        super().__init__()
        self._runtime = runtime
        self._toolset = toolset

    @override
    async def __call__(self, params: UpdateGoalParams) -> ToolReturnValue:
        if self._runtime.role != "root":
            return _root_only_error()

        store = _goal_store(self._runtime)
        if store.load() is None:
            return ToolError(
                message="No goal exists for this session. Use CreateGoal first.",
                brief="No goal",
            )

        if params.status == "blocked" and not (params.reason or "").strip():
            return ToolError(
                message='reason is required when setting status="blocked".',
                brief="Reason required",
            )

        try:
            match params.status:
                case "complete":
                    store.complete()
                case "blocked":
                    store.block((params.reason or "").strip())
                case "paused":
                    store.pause((params.reason or "").strip() or "Paused by agent")
                case "active":
                    store.resume()
        except GoalTransitionError as exc:
            return ToolError(message=str(exc), brief="Invalid transition")
        except GoalNotFoundError:
            return ToolError(message="No goal exists for this session.", brief="No goal")

        if params.status == "complete":
            sync_goal_tool_visibility(self._toolset, has_goal=False)
            return ToolOk(
                output=(
                    "Goal marked complete; the goal record has been cleared. Now write a "
                    "brief final summary for the user: what was achieved, the key changes "
                    "made, and anything left outstanding. Do not start new work."
                ),
                message="Goal completed",
                brief="Goal completed",
            )
        if params.status == "blocked":
            return ToolOk(
                output=(
                    f"Goal is now blocked ({params.reason}). It will not be advanced "
                    "autonomously. Briefly tell the user why you are blocked and what "
                    "input you need to continue."
                ),
                message="Goal blocked",
                brief="Goal blocked",
            )
        if params.status == "paused":
            return ToolOk(
                output=(
                    "Goal paused. It will not be advanced autonomously until the user "
                    "asks to resume it."
                ),
                message="Goal paused",
                brief="Goal paused",
            )
        return ToolOk(
            output=(
                "Goal resumed and active again. The driver will automatically continue "
                "with new turns after this one."
            ),
            message="Goal resumed",
            brief="Goal resumed",
        )


class SetGoalBudgetParams(BaseModel):
    max_turns: int | None = Field(default=None, gt=0, description="Hard turn limit.")
    max_tokens: int | None = Field(default=None, gt=0, description="Hard context-token limit.")
    max_seconds: int | None = Field(
        default=None,
        ge=MIN_GOAL_SECONDS,
        le=MAX_GOAL_SECONDS,
        description=f"Hard active-time limit in seconds ({MIN_GOAL_SECONDS}-{MAX_GOAL_SECONDS}).",
    )

    @model_validator(mode="after")
    def at_least_one_budget(self) -> "SetGoalBudgetParams":
        if self.max_turns is None and self.max_tokens is None and self.max_seconds is None:
            raise ValueError("At least one of max_turns, max_tokens, max_seconds is required")
        return self


class SetGoalBudget(CallableTool2[SetGoalBudgetParams]):
    name: str = SET_GOAL_BUDGET_TOOL_NAME
    description: str = load_desc(Path(__file__).parent / "set_goal_budget.md")
    params: type[SetGoalBudgetParams] = SetGoalBudgetParams

    def __init__(self, runtime: Runtime) -> None:
        super().__init__()
        self._runtime = runtime

    @override
    async def __call__(self, params: SetGoalBudgetParams) -> ToolReturnValue:
        if self._runtime.role != "root":
            return _root_only_error()

        store = _goal_store(self._runtime)
        if store.load() is None:
            return ToolError(
                message="No goal exists for this session. Use CreateGoal first.",
                brief="No goal",
            )

        budgets = GoalBudgets(
            max_turns=params.max_turns,
            max_tokens=params.max_tokens,
            max_seconds=params.max_seconds,
        )
        record = store.set_budgets(budgets)
        parts = []
        if record.budgets.max_turns is not None:
            parts.append(f"max_turns={record.budgets.max_turns}")
        if record.budgets.max_tokens is not None:
            parts.append(f"max_tokens={record.budgets.max_tokens}")
        if record.budgets.max_seconds is not None:
            parts.append(f"max_seconds={record.budgets.max_seconds}")
        return ToolOk(
            output=f"Goal budgets updated: {', '.join(parts)}.",
            message="Goal budgets updated",
            brief="Budgets updated",
        )
