import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";

enableMapSet();

interface AgentStats {
  completions_last_7_days: number;
  completions_last_3_days: number;
  total_cost: number;
  active: boolean;
  last_completion_date: string | null;
}

interface AgentStatsResult {
  agent_id: string;
  completions_last_7_days: number;
  completions_last_3_days: number;
  total_cost: number;
  active: boolean;
  last_completion_date: string | null;
  fetchedAt: string;
}

interface AgentsStatsState {
  agentStats: Map<string, AgentStatsResult>;
  isLoadingStats: Map<string, boolean>;
  statsErrors: Map<string, Error>;

  fetchAgentStats: (agentId: string) => Promise<AgentStats>;
  fetchMultipleAgentStats: (agentIds: string[]) => Promise<Map<string, AgentStats>>;
}

export const useAgentsStats = create<AgentsStatsState>((set, get) => ({
  agentStats: new Map(),
  isLoadingStats: new Map(),
  statsErrors: new Map(),

  fetchAgentStats: async (agentId: string) => {
    if (get().isLoadingStats.get(agentId) ?? false) {
      const existing = get().agentStats.get(agentId);
      return existing
        ? {
            completions_last_7_days: existing.completions_last_7_days,
            completions_last_3_days: existing.completions_last_3_days,
            total_cost: existing.total_cost,
            active: existing.active,
            last_completion_date: existing.last_completion_date,
          }
        : {
            completions_last_7_days: 0,
            completions_last_3_days: 0,
            total_cost: 0,
            active: false,
            last_completion_date: null,
          };
    }

    set(
      produce((state: AgentsStatsState) => {
        state.isLoadingStats.set(agentId, true);
        state.statsErrors.delete(agentId);
      })
    );

    try {
      // Single comprehensive query to get all stats at once
      const query = `
        SELECT 
          COALESCE(SUM(CASE WHEN created_at >= subtractDays(now(), 7) THEN 1 ELSE 0 END), 0) as total_completions_7d,
          COALESCE(SUM(CASE WHEN created_at >= subtractDays(now(), 3) THEN 1 ELSE 0 END), 0) as total_completions_3d,
          COALESCE(SUM(cost_usd), 0) as total_cost,
          MAX(created_at) as last_completion
        FROM completions 
        WHERE agent_id = '${agentId}'
      `;

      const response = await apiFetch(`/v1/completions/query?query=${encodeURIComponent(query)}`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch stats for agent ${agentId}: ${response.status} ${response.statusText}`);
      }

      const statsData = (await response.json()) as {
        total_completions_7d: number;
        total_completions_3d: number;
        total_cost: number;
        last_completion: string | null;
      }[];

      const stats = statsData[0] || {
        total_completions_7d: 0,
        total_completions_3d: 0,
        total_cost: 0,
        last_completion: null,
      };

      // Calculate if agent is active (within 3 days)
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const isActive = stats.last_completion ? new Date(stats.last_completion) > threeDaysAgo : false;

      const agentStatsResult: AgentStatsResult = {
        agent_id: agentId,
        completions_last_7_days: stats.total_completions_7d || 0,
        completions_last_3_days: stats.total_completions_3d || 0,
        total_cost: stats.total_cost || 0,
        active: isActive,
        last_completion_date: stats.last_completion,
        fetchedAt: new Date().toISOString(),
      };

      set(
        produce((state: AgentsStatsState) => {
          state.agentStats.set(agentId, agentStatsResult);
          state.isLoadingStats.set(agentId, false);
        })
      );

      return {
        completions_last_7_days: agentStatsResult.completions_last_7_days,
        completions_last_3_days: agentStatsResult.completions_last_3_days,
        total_cost: agentStatsResult.total_cost,
        active: agentStatsResult.active,
        last_completion_date: agentStatsResult.last_completion_date,
      };
    } catch (error) {
      console.error(`Failed to fetch stats for agent ${agentId}:`, error);

      set(
        produce((state: AgentsStatsState) => {
          state.statsErrors.set(agentId, error as Error);
          state.isLoadingStats.set(agentId, false);
        })
      );

      return {
        completions_last_7_days: 0,
        completions_last_3_days: 0,
        total_cost: 0,
        active: false,
        last_completion_date: null,
      };
    }
  },

  fetchMultipleAgentStats: async (agentIds: string[]) => {
    if (agentIds.length === 0) {
      return new Map<string, AgentStats>();
    }

    // Mark all agents as loading
    set(
      produce((state: AgentsStatsState) => {
        agentIds.forEach((agentId) => {
          state.isLoadingStats.set(agentId, true);
          state.statsErrors.delete(agentId);
        });
      })
    );

    try {
      // Create IN clause with properly quoted agent IDs
      const agentIdsString = agentIds.map((id) => `'${id}'`).join(", ");

      // Single comprehensive query for all agents
      const query = `
        SELECT 
          agent_id,
          COALESCE(SUM(CASE WHEN created_at >= subtractDays(now(), 7) THEN 1 ELSE 0 END), 0) as total_completions_7d,
          COALESCE(SUM(CASE WHEN created_at >= subtractDays(now(), 3) THEN 1 ELSE 0 END), 0) as total_completions_3d,
          COALESCE(SUM(cost_usd), 0) as total_cost,
          MAX(created_at) as last_completion
        FROM completions 
        WHERE agent_id IN (${agentIdsString}) 
        GROUP BY agent_id
      `;

      const response = await apiFetch(`/v1/completions/query?query=${encodeURIComponent(query)}`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch stats for multiple agents: ${response.status} ${response.statusText}`);
      }

      const statsData = (await response.json()) as {
        agent_id: string;
        total_completions_7d: number;
        total_completions_3d: number;
        total_cost: number;
        last_completion: string | null;
      }[];

      // Calculate the date 3 days ago for active status check
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const statsMap = new Map<string, AgentStats>();

      // Process results and create map
      statsData.forEach((row) => {
        const isActive = row.last_completion ? new Date(row.last_completion) > threeDaysAgo : false;

        const agentStatsResult: AgentStatsResult = {
          agent_id: row.agent_id,
          completions_last_7_days: row.total_completions_7d || 0,
          completions_last_3_days: row.total_completions_3d || 0,
          total_cost: row.total_cost || 0,
          active: isActive,
          last_completion_date: row.last_completion,
          fetchedAt: new Date().toISOString(),
        };

        // Store in state
        set(
          produce((state: AgentsStatsState) => {
            state.agentStats.set(row.agent_id, agentStatsResult);
            state.isLoadingStats.set(row.agent_id, false);
          })
        );

        // Add to return map
        statsMap.set(row.agent_id, {
          completions_last_7_days: agentStatsResult.completions_last_7_days,
          completions_last_3_days: agentStatsResult.completions_last_3_days,
          total_cost: agentStatsResult.total_cost,
          active: agentStatsResult.active,
          last_completion_date: agentStatsResult.last_completion_date,
        });
      });

      // For agents not in the result (no completions), set them to 0
      agentIds.forEach((agentId) => {
        if (!statsMap.has(agentId)) {
          const agentStatsResult: AgentStatsResult = {
            agent_id: agentId,
            completions_last_7_days: 0,
            completions_last_3_days: 0,
            total_cost: 0,
            active: false,
            last_completion_date: null,
            fetchedAt: new Date().toISOString(),
          };

          set(
            produce((state: AgentsStatsState) => {
              state.agentStats.set(agentId, agentStatsResult);
              state.isLoadingStats.set(agentId, false);
            })
          );

          statsMap.set(agentId, {
            completions_last_7_days: 0,
            completions_last_3_days: 0,
            total_cost: 0,
            active: false,
            last_completion_date: null,
          });
        }
      });

      return statsMap;
    } catch (error) {
      console.error("Failed to fetch stats for multiple agents:", error);

      // Mark all agents as not loading and set error
      set(
        produce((state: AgentsStatsState) => {
          agentIds.forEach((agentId) => {
            state.statsErrors.set(agentId, error as Error);
            state.isLoadingStats.set(agentId, false);
          });
        })
      );

      // Return empty stats for all agents
      const statsMap = new Map<string, AgentStats>();
      agentIds.forEach((agentId) => {
        statsMap.set(agentId, {
          completions_last_7_days: 0,
          completions_last_3_days: 0,
          total_cost: 0,
          active: false,
          last_completion_date: null,
        });
      });
      return statsMap;
    }
  },
}));

export const useOrFetchAgentStats = (agentId: string | undefined) => {
  const fetchAgentStats = useAgentsStats((state) => state.fetchAgentStats);
  const agentStats = useAgentsStats((state) => (agentId ? state.agentStats.get(agentId) : undefined));

  const isLoading = useAgentsStats((state) => (agentId ? (state.isLoadingStats.get(agentId) ?? false) : false));

  const error = useAgentsStats((state) => (agentId ? state.statsErrors.get(agentId) : undefined));

  const agentStatsRef = useRef(agentStats);
  agentStatsRef.current = agentStats;

  const update = useCallback(() => {
    if (agentId) {
      fetchAgentStats(agentId);
    }
  }, [fetchAgentStats, agentId]);

  useEffect(() => {
    if (!agentStatsRef.current && agentId) {
      fetchAgentStats(agentId);
    }
  }, [fetchAgentStats, agentId]);

  return {
    stats: agentStats
      ? {
          completions_last_7_days: agentStats.completions_last_7_days,
          total_cost: agentStats.total_cost,
          active: agentStats.active,
          last_completion_date: agentStats.last_completion_date,
        }
      : undefined,
    isLoading,
    error,
    update,
  };
};

export const useOrFetchMultipleAgentStats = (agentIds: string[]) => {
  const fetchMultipleAgentStats = useAgentsStats((state) => state.fetchMultipleAgentStats);
  const agentStats = useAgentsStats((state) => state.agentStats);

  const allStats = new Map<string, AgentStats>();
  const anyLoading = agentIds.some((id) => useAgentsStats.getState().isLoadingStats.get(id) ?? false);

  agentIds.forEach((agentId) => {
    const stats = agentStats.get(agentId);
    if (stats) {
      allStats.set(agentId, {
        completions_last_7_days: stats.completions_last_7_days,
        completions_last_3_days: stats.completions_last_3_days,
        total_cost: stats.total_cost,
        active: stats.active,
        last_completion_date: stats.last_completion_date,
      });
    }
  });

  const allStatsRef = useRef(allStats);
  allStatsRef.current = allStats;

  const update = useCallback(() => {
    if (agentIds.length > 0) {
      fetchMultipleAgentStats(agentIds);
    }
  }, [fetchMultipleAgentStats, agentIds]);

  useEffect(() => {
    // Check if we have stats for all agents, if not fetch them
    const missingStats = agentIds.filter((id) => !allStatsRef.current.has(id));
    if (missingStats.length > 0) {
      fetchMultipleAgentStats(agentIds);
    }
  }, [fetchMultipleAgentStats, agentIds]);

  return {
    allStats,
    isLoading: anyLoading,
    update,
  };
};
