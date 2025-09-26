import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { createErrorFromResponse } from "@/lib/apiError";
import { apiFetch } from "@/lib/apiFetch";

enableMapSet();

// Types based on actual API response from /v1/agents
interface Agent {
  id: string;
  name: string;
  created_at: string;
}

interface AgentsState {
  agents: Agent[];
  isLoadingAgents: boolean;
  agentsError: Error | undefined;

  fetchAgents: () => Promise<void>;
}

export const useAgents = create<AgentsState>((set, get) => ({
  agents: [],
  isLoadingAgents: false,
  agentsError: undefined,

  fetchAgents: async () => {
    if (get().isLoadingAgents) return;

    set(
      produce((state: AgentsState) => {
        state.isLoadingAgents = true;
        state.agentsError = undefined;
      })
    );

    try {
      const response = await apiFetch("/v1/agents", {
        method: "GET",
      });

      if (!response.ok) {
        throw await createErrorFromResponse(response);
      }

      const agentsData = await response.json();
      const agents: Agent[] = agentsData.items || [];

      set(
        produce((state: AgentsState) => {
          state.agents = agents;
          state.isLoadingAgents = false;
        })
      );
    } catch (error) {
      // Skip console logging for API errors to reduce noise
      const errorObj = error as Error & { isApiError?: boolean };
      if (!errorObj.isApiError) {
        console.error("Failed to fetch agents:", error);
      }

      set(
        produce((state: AgentsState) => {
          state.agentsError = error as Error;
          state.isLoadingAgents = false;
        })
      );
    }
  },
}));

export const useOrFetchAgents = () => {
  const fetchAgents = useAgents((state) => state.fetchAgents);
  const agents = useAgents((state) => state.agents);
  const isLoading = useAgents((state) => state.isLoadingAgents);
  const error = useAgents((state) => state.agentsError);

  const agentsRef = useRef(agents);
  agentsRef.current = agents;

  const update = useCallback(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    if (agentsRef.current.length === 0) {
      fetchAgents();
    }
  }, [fetchAgents]);

  return {
    agents,
    isLoading,
    error,
    update,
  };
};
