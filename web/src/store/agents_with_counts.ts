import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import { AgentWithCompletionCount } from "@/types/models";

enableMapSet();

interface AgentsWithCountsState {
  agents: AgentWithCompletionCount[];
  isLoadingAgents: boolean;
  agentsError: Error | undefined;

  fetchAgentsWithCounts: () => Promise<void>;
}

export const useAgentsWithCounts = create<AgentsWithCountsState>(
  (set, get) => ({
    agents: [],
    isLoadingAgents: false,
    agentsError: undefined,

    fetchAgentsWithCounts: async () => {
      if (get().isLoadingAgents) return;

      set(
        produce((state: AgentsWithCountsState) => {
          state.isLoadingAgents = true;
          state.agentsError = undefined;
        })
      );

      try {
        const query =
          "SELECT agent_id, COUNT(*) as completion_count FROM completions GROUP BY agent_id ORDER BY completion_count DESC";
        const response = await apiFetch(
          `/v1/completions/query?query=${encodeURIComponent(query)}`,
          {
            method: "GET",
          }
        );

        if (!response.ok) {
          throw new Error(
            `Failed to fetch agents with counts: ${response.status} ${response.statusText}`
          );
        }

        const result = await response.json();
        const agents: AgentWithCompletionCount[] = (
          Array.isArray(result) ? result : result.data || []
        ).map((item: Record<string, unknown>) => ({
          agent_id: String(item.agent_id),
          completion_count: Number(
            item.completion_count || item["COUNT(*) as completion_count"] || 0
          ),
        }));

        set(
          produce((state: AgentsWithCountsState) => {
            state.agents = agents;
            state.isLoadingAgents = false;
          })
        );
      } catch (error) {
        console.error("Failed to fetch agents with counts:", error);

        set(
          produce((state: AgentsWithCountsState) => {
            state.agentsError = error as Error;
            state.isLoadingAgents = false;
          })
        );
      }
    },
  })
);

export const useOrFetchAgentsWithCounts = () => {
  const fetchAgentsWithCounts = useAgentsWithCounts(
    (state) => state.fetchAgentsWithCounts
  );
  const agents = useAgentsWithCounts((state) => state.agents);
  const isLoading = useAgentsWithCounts((state) => state.isLoadingAgents);
  const error = useAgentsWithCounts((state) => state.agentsError);

  const agentsRef = useRef(agents);
  agentsRef.current = agents;

  const update = useCallback(() => {
    fetchAgentsWithCounts();
  }, [fetchAgentsWithCounts]);

  useEffect(() => {
    if (agentsRef.current.length === 0) {
      fetchAgentsWithCounts();
    }
  }, [fetchAgentsWithCounts]);

  return {
    agents,
    isLoading,
    error,
    update,
  };
};
