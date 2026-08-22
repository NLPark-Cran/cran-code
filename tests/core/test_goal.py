"""Tests for cran_code.soul.goal (goal mode P1 backend core)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from cran_code.soul.goal import (
    DEFAULT_GOAL_TURN_BUDGET,
    GoalBudgets,
    GoalDriver,
    GoalExistsError,
    GoalNotFoundError,
    GoalStore,
    GoalTransitionError,
    budget_exceeded,
    budget_pressure,
    build_continuation_prompt,
    build_goal_reminder,
    build_light_reminder,
    sync_goal_tool_visibility,
)
from cran_code.tools.goal import CreateGoal, GetGoal, SetGoalBudget, UpdateGoal
from tests.conftest import tool_call_context


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def session_dir(tmp_path: Path) -> Path:
    d = tmp_path / "session"
    d.mkdir()
    return d


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def store(session_dir: Path, clock: FakeClock) -> GoalStore:
    return GoalStore(session_dir, clock=clock)


# ---------------------------------------------------------------------------
# Store CRUD + persistence
# ---------------------------------------------------------------------------


def test_create_and_load_roundtrip(store: GoalStore) -> None:
    record = store.create("ship the release", criteria="all tests green")

    assert record.status == "active"
    assert record.active_since == pytest.approx(1000.0)
    assert store.path.exists()

    loaded = GoalStore(store.path.parent).load()
    assert loaded is not None
    assert loaded.objective == "ship the release"
    assert loaded.criteria == "all tests green"
    assert loaded.status == "active"


def test_load_missing_and_corrupt(store: GoalStore) -> None:
    assert store.load() is None
    store.path.write_text('{"objective": ', encoding="utf-8")
    assert store.load() is None
    store.path.write_text('{"objective": 42}', encoding="utf-8")
    assert store.load() is None


def test_create_refuses_when_goal_exists(store: GoalStore) -> None:
    store.create("first")
    with pytest.raises(GoalExistsError):
        store.create("second")


def test_clear(store: GoalStore) -> None:
    store.create("gone soon")
    store.clear()
    assert store.load() is None
    assert not store.path.exists()
    store.clear()  # idempotent


def test_transitions_require_existing_goal(store: GoalStore) -> None:
    with pytest.raises(GoalNotFoundError):
        store.pause("x")
    with pytest.raises(GoalNotFoundError):
        store.resume()
    with pytest.raises(GoalNotFoundError):
        store.block("x")
    with pytest.raises(GoalNotFoundError):
        store.complete()
    with pytest.raises(GoalNotFoundError):
        store.cancel()
    with pytest.raises(GoalNotFoundError):
        store.set_budgets(GoalBudgets(max_turns=5))


# ---------------------------------------------------------------------------
# Transition matrix
# ---------------------------------------------------------------------------


def test_pause_resume_cycle(store: GoalStore, clock: FakeClock) -> None:
    store.create("goal")
    paused = store.pause("user asked")
    assert paused.status == "paused"
    assert paused.stop_reason == "user asked"
    assert paused.active_since is None

    clock.advance(5)
    resumed = store.resume()
    assert resumed.status == "active"
    assert resumed.stop_reason is None
    assert resumed.active_since == pytest.approx(1005.0)


def test_invalid_transitions(store: GoalStore) -> None:
    store.create("goal")
    with pytest.raises(GoalTransitionError):
        store.resume()  # already active
    store.pause("p")
    with pytest.raises(GoalTransitionError):
        store.pause("again")  # already paused
    store.block("b")  # paused -> blocked is allowed
    with pytest.raises(GoalTransitionError):
        store.block("again")  # already blocked
    resumed = store.resume()  # blocked -> active is allowed
    assert resumed.status == "active"


def test_complete_clears_record(store: GoalStore) -> None:
    store.create("goal")
    final = store.complete()
    assert final.stats.turns == 0
    assert store.load() is None
    assert not store.path.exists()


def test_cancel_clears_record(store: GoalStore) -> None:
    store.create("goal")
    store.cancel()
    assert store.load() is None


def test_set_budgets(store: GoalStore) -> None:
    store.create("goal")
    record = store.set_budgets(GoalBudgets(max_turns=10, max_seconds=600))
    assert record.budgets.max_turns == 10
    assert record.budgets.max_seconds == 600
    assert GoalStore(store.path.parent).load().budgets.max_turns == 10  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Stats accounting
# ---------------------------------------------------------------------------


def test_stats_active_seconds_across_pause_resume(store: GoalStore, clock: FakeClock) -> None:
    store.create("goal")
    clock.advance(10)
    paused = store.pause("p")
    assert paused.stats.active_seconds == pytest.approx(10.0)

    clock.advance(100)  # paused time must not count
    store.resume()
    clock.advance(15)
    blocked = store.block("b")
    assert blocked.stats.active_seconds == pytest.approx(25.0)


def test_record_turn_increments_stats(store: GoalStore) -> None:
    store.create("goal")
    record = store.record_turn(tokens=1234)
    assert record.stats.turns == 1
    assert record.stats.tokens == 1234
    record = store.record_turn(tokens=2000)
    assert record.stats.turns == 2
    assert record.stats.tokens == 2000  # latest context token count, not cumulative


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------


def test_budget_exceeded_turns(store: GoalStore) -> None:
    store.create("goal", budgets=GoalBudgets(max_turns=2))
    store.record_turn(0)
    assert budget_exceeded(store.load()) is None  # type: ignore[arg-type]
    store.record_turn(0)
    reason = budget_exceeded(store.load())  # type: ignore[arg-type]
    assert reason is not None and "Turn budget" in reason


def test_budget_exceeded_default_turn_cap(store: GoalStore) -> None:
    store.create("goal")
    for _ in range(DEFAULT_GOAL_TURN_BUDGET - 1):
        assert budget_exceeded(store.load()) is None  # type: ignore[arg-type]
        store.record_turn(0)
    store.record_turn(0)
    assert budget_exceeded(store.load()) is not None  # type: ignore[arg-type]


def test_budget_exceeded_tokens_and_seconds(store: GoalStore, clock: FakeClock) -> None:
    store.create("goal", budgets=GoalBudgets(max_tokens=100, max_seconds=60))
    store.record_turn(tokens=150)
    assert "Token budget" in (budget_exceeded(store.load()) or "")  # type: ignore[arg-type]

    store2 = GoalStore(store.path.parent, clock=clock)
    store2.clear()
    store2.create("goal", budgets=GoalBudgets(max_seconds=60))
    clock.advance(61)
    assert "Time budget" in (budget_exceeded(store2.load()) or "")  # type: ignore[arg-type]


def test_budget_pressure_threshold(store: GoalStore) -> None:
    store.create("goal", budgets=GoalBudgets(max_turns=4))
    store.record_turn(0)
    assert not budget_pressure(store.load())  # type: ignore[arg-type]
    store.record_turn(0)
    store.record_turn(0)
    assert budget_pressure(store.load())  # type: ignore[arg-type]  # 3/4 = 75%


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def test_full_reminder_content(store: GoalStore) -> None:
    record = store.create("refactor the parser", criteria="pytest passes")
    reminder = build_goal_reminder(record, pressure=False)

    assert "refactor the parser" in reminder
    assert "pytest passes" in reminder
    assert "user data" in reminder  # hardening line
    assert 'UpdateGoal(status="complete")' in reminder
    assert 'UpdateGoal(status="blocked", reason=...)' in reminder
    assert "goal mode" in reminder
    assert "Budget notice" not in reminder

    pressured = build_goal_reminder(record, pressure=True)
    assert "Budget notice" in pressured


def test_light_reminder_content(store: GoalStore) -> None:
    store.create("goal")
    paused = store.pause("user paused")
    reminder = build_light_reminder(paused)
    assert "paused" in reminder
    assert "user paused" in reminder
    assert "NOT" in reminder


def test_continuation_prompt_content() -> None:
    prompt = build_continuation_prompt(pressure=False)
    assert "Continue working toward the active goal" in prompt
    assert "Budget notice" not in prompt
    pressured = build_continuation_prompt(pressure=True)
    assert "Budget notice" in pressured


# ---------------------------------------------------------------------------
# Wire event emission
# ---------------------------------------------------------------------------


def test_goal_updated_events_emitted_when_wire_active(store: GoalStore) -> None:
    from types import SimpleNamespace

    from cran_code.soul import _current_wire
    from cran_code.wire.types import GoalUpdated

    sent: list[object] = []
    fake_wire = SimpleNamespace(soul_side=SimpleNamespace(send=sent.append))
    token = _current_wire.set(fake_wire)
    try:
        store.create("goal")
        store.record_turn(10)
        store.pause("p")
        store.resume()
        store.complete()
    finally:
        _current_wire.reset(token)

    changes = [m.change for m in sent]
    assert changes == ["created", "updated", "paused", "resumed", "completed"]
    assert all(isinstance(m, GoalUpdated) for m in sent)
    assert sent[0].snapshot["objective"] == "goal"  # type: ignore[index]
    # completed event carries the final snapshot, then the file is cleared
    assert sent[-1].snapshot is not None  # type: ignore[index]
    assert store.load() is None


def test_goal_events_noop_without_wire(store: GoalStore) -> None:
    store.create("goal")  # must not raise
    store.cancel()


# ---------------------------------------------------------------------------
# Restore downgrade
# ---------------------------------------------------------------------------


def test_restore_downgrade(store: GoalStore) -> None:
    store.create("goal")
    downgraded = store.restore_downgrade()
    assert downgraded is not None
    assert downgraded.status == "paused"
    assert downgraded.stop_reason == "session restarted"
    # idempotent: second call is a no-op
    again = store.restore_downgrade()
    assert again is not None and again.status == "paused"


def test_restore_downgrade_keeps_paused_and_blocked(store: GoalStore) -> None:
    store.create("goal")
    store.pause("p")
    assert store.restore_downgrade().status == "paused"  # type: ignore[union-attr]
    assert store.restore_downgrade().stop_reason == "p"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Driver loop (fake turn runner)
# ---------------------------------------------------------------------------


def test_driver_stops_when_goal_completed_mid_run(session_dir: Path, clock: FakeClock) -> None:
    driver = GoalDriver(session_dir, token_counter=lambda: 100, clock=clock)
    store = driver.store
    store.create("finish the task")

    user_input = driver.prepare_turn_input("please do it autonomously")
    assert isinstance(user_input, str)
    assert "finish the task" in user_input
    assert "please do it autonomously" in user_input

    continuations: list[str] = []
    for turn in range(10):
        # ... fake turn runs here ...
        if turn == 2:
            store.complete()  # model completes the goal mid-turn
        cont = driver.after_turn()
        if cont is None:
            break
        continuations.append(cont)

    assert len(continuations) == 2
    assert all("Continue working toward the active goal" in c for c in continuations)
    assert store.load() is None


def test_driver_error_pauses_goal(session_dir: Path, clock: FakeClock) -> None:
    driver = GoalDriver(session_dir, clock=clock)
    store = driver.store
    store.create("goal")

    driver.pause_on_error("API status error 500")
    record = store.load()
    assert record is not None
    assert record.status == "paused"
    assert "API status error 500" in (record.stop_reason or "")
    assert driver.after_turn() is None  # no autonomous continuation after error


def test_driver_default_turn_cap_stops_never_completing_goal(
    session_dir: Path, clock: FakeClock
) -> None:
    driver = GoalDriver(session_dir, clock=clock)
    store = driver.store
    store.create("never finishes")

    turns = 0
    for _ in range(DEFAULT_GOAL_TURN_BUDGET + 10):
        if driver.after_turn() is None:
            break
        turns += 1

    record = store.load()
    assert record is not None
    assert turns == DEFAULT_GOAL_TURN_BUDGET - 1  # last turn returns None instead of a prompt
    assert record.stats.turns == DEFAULT_GOAL_TURN_BUDGET
    assert record.status == "blocked"
    assert "Turn budget" in (record.stop_reason or "")


def test_driver_explicit_budget_blocks_and_emits_budget_event(
    session_dir: Path, clock: FakeClock
) -> None:
    from types import SimpleNamespace

    from cran_code.soul import _current_wire
    from cran_code.wire.types import GoalUpdated

    sent: list[object] = []
    fake_wire = SimpleNamespace(soul_side=SimpleNamespace(send=sent.append))
    token = _current_wire.set(fake_wire)
    try:
        driver = GoalDriver(session_dir, clock=clock)
        store = driver.store
        store.create("goal", budgets=GoalBudgets(max_turns=2))

        assert driver.after_turn() is not None  # turn 1
        assert driver.after_turn() is None  # turn 2 -> budget exhausted
    finally:
        _current_wire.reset(token)

    record = store.load()
    assert record is not None and record.status == "blocked"
    budget_events = [m for m in sent if isinstance(m, GoalUpdated) and m.change == "budget"]
    assert len(budget_events) == 1
    assert budget_events[0].snapshot["status"] == "blocked"  # type: ignore[index]


def test_driver_pressure_note_in_continuation(session_dir: Path, clock: FakeClock) -> None:
    driver = GoalDriver(session_dir, clock=clock)
    store = driver.store
    store.create("goal", budgets=GoalBudgets(max_turns=4))
    store.record_turn(0)
    store.record_turn(0)
    cont = driver.after_turn()  # turn 3 -> 75% of budget
    assert cont is not None and "Budget notice" in cont


def test_driver_prepare_input_variants(session_dir: Path, clock: FakeClock) -> None:
    from cran_code.wire.types import TextPart

    driver = GoalDriver(session_dir, clock=clock)
    # No goal: input untouched
    assert driver.prepare_turn_input("hello") == "hello"

    store = driver.store
    store.create("goal")
    # list[ContentPart] input: reminder prepended as a TextPart
    parts = driver.prepare_turn_input([TextPart(text="real input")])
    assert isinstance(parts, list)
    assert isinstance(parts[0], TextPart)
    assert "goal mode" in parts[0].text
    assert parts[1].text == "real input"

    # paused goal: light reminder
    store.pause("p")
    light = driver.prepare_turn_input("hi")
    assert isinstance(light, str) and "paused" in light
    assert "Budget notice" not in light


# ---------------------------------------------------------------------------
# Tool visibility sync
# ---------------------------------------------------------------------------


def test_sync_goal_tool_visibility(runtime, toolset, approval) -> None:
    toolset.add(CreateGoal(runtime, toolset, approval))
    toolset.add(UpdateGoal(runtime, toolset))
    toolset.add(SetGoalBudget(runtime))

    sync_goal_tool_visibility(toolset, has_goal=False)
    names = {t.name for t in toolset.tools}
    assert "CreateGoal" in names
    assert "UpdateGoal" not in names
    assert "SetGoalBudget" not in names

    sync_goal_tool_visibility(toolset, has_goal=True)
    names = {t.name for t in toolset.tools}
    assert {"UpdateGoal", "SetGoalBudget"} <= names


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def test_create_goal_tool(runtime, toolset, approval) -> None:
    toolset.add(UpdateGoal(runtime, toolset))
    toolset.add(SetGoalBudget(runtime))
    sync_goal_tool_visibility(toolset, has_goal=False)
    assert "UpdateGoal" not in {t.name for t in toolset.tools}

    tool = CreateGoal(runtime, toolset, approval)
    with tool_call_context("CreateGoal"):
        result = await tool(CreateGoal.params(objective="ship it", max_turns=5))
    assert not result.is_error
    record = GoalStore(runtime.session.dir).load()
    assert record is not None
    assert record.objective == "ship it"
    assert record.budgets.max_turns == 5
    # creation unhides the goal mutation tools
    assert {"UpdateGoal", "SetGoalBudget"} <= {t.name for t in toolset.tools}
    # create again -> refused
    with tool_call_context("CreateGoal"):
        again = await tool(CreateGoal.params(objective="another"))
    assert again.is_error
    assert "already exists" in str(again.output) or "already exists" in again.message


async def test_create_goal_rejected_by_user(runtime, toolset, monkeypatch) -> None:
    from cran_code.soul.approval import Approval, ApprovalResult

    async def fake_request(self, *args, **kwargs):
        return ApprovalResult(approved=False)

    monkeypatch.setattr(Approval, "request", fake_request)
    tool = CreateGoal(runtime, toolset, Approval(yolo=False))
    with tool_call_context("CreateGoal"):
        result = await tool(CreateGoal.params(objective="ship it"))
    assert result.is_error
    assert GoalStore(runtime.session.dir).load() is None


async def test_get_goal_tool(runtime) -> None:
    tool = GetGoal(runtime)
    empty = await tool(GetGoal.params())
    assert not empty.is_error
    assert "No goal" in str(empty.output)

    GoalStore(runtime.session.dir).create("my goal", criteria="done")
    got = await tool(GetGoal.params())
    assert "my goal" in str(got.output)
    assert "done" in str(got.output)


async def test_update_goal_tool_flow(runtime, toolset) -> None:
    store = GoalStore(runtime.session.dir)
    tool = UpdateGoal(runtime, toolset)

    # no goal -> error
    result = await tool(UpdateGoal.params(status="paused"))
    assert result.is_error

    store.create("goal")
    # blocked requires reason
    no_reason = await tool(UpdateGoal.params(status="blocked"))
    assert no_reason.is_error

    blocked = await tool(UpdateGoal.params(status="blocked", reason="need api key"))
    assert not blocked.is_error
    assert store.load().status == "blocked"  # type: ignore[union-attr]

    resumed = await tool(UpdateGoal.params(status="active"))
    assert not resumed.is_error
    assert store.load().status == "active"  # type: ignore[union-attr]

    paused = await tool(UpdateGoal.params(status="paused", reason="user break"))
    assert not paused.is_error
    assert store.load().status == "paused"  # type: ignore[union-attr]

    # invalid transition: already paused
    again = await tool(UpdateGoal.params(status="paused"))
    assert again.is_error

    completed = await tool(UpdateGoal.params(status="complete"))
    assert not completed.is_error
    assert "brief final summary" in str(completed.output)
    assert store.load() is None


async def test_set_goal_budget_tool(runtime) -> None:
    store = GoalStore(runtime.session.dir)
    tool = SetGoalBudget(runtime)

    no_goal = await tool(SetGoalBudget.params(max_turns=3))
    assert no_goal.is_error

    store.create("goal")
    ok = await tool(SetGoalBudget.params(max_turns=3, max_seconds=600))
    assert not ok.is_error
    record = store.load()
    assert record is not None
    assert record.budgets.max_turns == 3
    assert record.budgets.max_seconds == 600


async def test_goal_params_validation() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CreateGoal.params(objective="")
    with pytest.raises(ValidationError):
        CreateGoal.params(objective="   ")
    with pytest.raises(ValidationError):
        CreateGoal.params(objective="x" * 4001)
    with pytest.raises(ValidationError):
        CreateGoal.params(objective="ok", max_turns=0)
    with pytest.raises(ValidationError):
        CreateGoal.params(objective="ok", max_seconds=30)  # below MIN_GOAL_SECONDS
    with pytest.raises(ValidationError):
        CreateGoal.params(objective="ok", max_seconds=90000)  # above MAX_GOAL_SECONDS
    with pytest.raises(ValidationError):
        SetGoalBudget.params()  # at least one budget required


async def test_goal_tools_root_only(runtime, toolset, approval) -> None:
    subagent_runtime = dataclasses.replace(runtime, role="subagent")
    GoalStore(subagent_runtime.session.dir).create("goal")

    with tool_call_context("CreateGoal"):
        create_result = await CreateGoal(subagent_runtime, toolset, approval)(
            CreateGoal.params(objective="x")
        )
    assert create_result.is_error

    get_result = await GetGoal(subagent_runtime)(GetGoal.params())
    assert get_result.is_error

    update_result = await UpdateGoal(subagent_runtime, toolset)(
        UpdateGoal.params(status="complete")
    )
    assert update_result.is_error

    budget_result = await SetGoalBudget(subagent_runtime)(SetGoalBudget.params(max_turns=3))
    assert budget_result.is_error

    # the goal must be untouched
    assert GoalStore(runtime.session.dir).load() is not None
