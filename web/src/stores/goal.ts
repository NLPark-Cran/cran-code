import { create } from "zustand";

export type GoalStatus = "active" | "paused" | "blocked";

export type GoalChange =
  | "created"
  | "updated"
  | "completed"
  | "paused"
  | "blocked"
  | "resumed"
  | "cleared"
  | "budget";

/** Mirrors `GoalRecord` in `src/cran_code/soul/goal.py` (unix-second timestamps). */
export type GoalSnapshot = {
  objective: string;
  criteria: string | null;
  status: GoalStatus;
  stop_reason: string | null;
  budgets: {
    max_turns: number | null;
    max_tokens: number | null;
    max_seconds: number | null;
  };
  stats: {
    turns: number;
    tokens: number;
    active_seconds: number;
  };
  created_at: number;
  updated_at: number;
  active_since: number | null;
};

/** Fallback turn budget enforced by the backend when `budgets.max_turns` is null. */
export const DEFAULT_GOAL_TURN_BUDGET = 30;

export const effectiveGoalMaxTurns = (goal: GoalSnapshot): number =>
  goal.budgets.max_turns ?? DEFAULT_GOAL_TURN_BUDGET;

/** Total active seconds including the in-progress active interval. */
export const currentGoalActiveSeconds = (
  goal: GoalSnapshot,
  nowSeconds: number,
): number => {
  let total = goal.stats.active_seconds;
  if (goal.active_since !== null) {
    total += Math.max(0, nowSeconds - goal.active_since);
  }
  return total;
};

type GoalStore = {
  goal: GoalSnapshot | null;
  setFromSnapshot: (snapshot: GoalSnapshot | null) => void;
  clear: () => void;
};

export const useGoalStore = create<GoalStore>((set) => ({
  goal: null,
  setFromSnapshot: (snapshot) => set({ goal: snapshot }),
  clear: () => set({ goal: null }),
}));
