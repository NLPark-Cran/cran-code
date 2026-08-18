import { create } from "zustand";

export type SwarmAgentStatus =
  | "idle"
  | "running_foreground"
  | "running_background"
  | "completed"
  | "failed"
  | "killed";

export type SwarmAgent = {
  agentId: string;
  subagentType: string;
  description: string;
  status: SwarmAgentStatus;
  /** Unix seconds, from the backend */
  updatedAt: number;
  lastTaskId: string | null;
  /** Number of inner SubagentEvent steps observed for this agent */
  stepCount: number;
  /** Unix ms, client-side timestamp of the last observed inner step */
  lastActivityAt: number | null;
};

/** Payload of the `SubagentStatus` wire event. */
export type SwarmStatusEventPayload = {
  agent_id: string;
  subagent_type: string;
  description: string;
  status: SwarmAgentStatus;
  updated_at: number;
  last_task_id: string | null;
};

/** Item of the `GET /api/sessions/{id}/subagents` snapshot. */
export type SwarmSnapshotItem = SwarmStatusEventPayload & {
  created_at?: number;
  launch_spec?: Record<string, unknown>;
};

function fromStatusPayload(
  event: SwarmStatusEventPayload,
  prev?: SwarmAgent,
): SwarmAgent {
  return {
    agentId: event.agent_id,
    subagentType: event.subagent_type ?? prev?.subagentType ?? "",
    description: event.description ?? prev?.description ?? "",
    status: event.status,
    updatedAt: event.updated_at,
    lastTaskId: event.last_task_id ?? null,
    stepCount: prev?.stepCount ?? 0,
    lastActivityAt: prev?.lastActivityAt ?? null,
  };
}

type SwarmStore = {
  agents: Record<string, SwarmAgent>;
  upsertFromStatus: (event: SwarmStatusEventPayload) => void;
  touchActivity: (agentId: string) => void;
  hydrate: (items: SwarmSnapshotItem[]) => void;
  clear: () => void;
};

export const useSwarmStore = create<SwarmStore>((set) => ({
  agents: {},

  upsertFromStatus: (event) =>
    set((s) => {
      if (!event.agent_id) return s;
      return {
        agents: {
          ...s.agents,
          [event.agent_id]: fromStatusPayload(event, s.agents[event.agent_id]),
        },
      };
    }),

  touchActivity: (agentId) =>
    set((s) => {
      const prev = s.agents[agentId];
      if (!prev) return s;
      return {
        agents: {
          ...s.agents,
          [agentId]: {
            ...prev,
            stepCount: prev.stepCount + 1,
            lastActivityAt: Date.now(),
          },
        },
      };
    }),

  hydrate: (items) =>
    set((s) => {
      const agents: Record<string, SwarmAgent> = {};
      for (const item of items) {
        if (!item.agent_id) continue;
        const prev = s.agents[item.agent_id];
        // Keep a fresher live entry if one arrived after the snapshot was taken.
        if (prev && prev.updatedAt > item.updated_at) {
          agents[item.agent_id] = prev;
        } else {
          agents[item.agent_id] = fromStatusPayload(item, prev);
        }
      }
      return { agents };
    }),

  clear: () => set({ agents: {} }),
}));

export const isSwarmAgentRunning = (status: SwarmAgentStatus): boolean =>
  status === "running_foreground" || status === "running_background";

export const selectRunningSwarmCount = (s: SwarmStore): number =>
  Object.values(s.agents).filter((a) => isSwarmAgentRunning(a.status)).length;
