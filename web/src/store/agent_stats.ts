import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";

enableMapSet();

// Interfaces for completion data
interface Completion extends Record<string, unknown> {
  id: string;
  agent_id: string;
  created_at: string;
  cost_usd: number;
  duration_seconds: number;
  version_model: string;
  input_messages?: string;
  output_messages?: string;
  output_error?: string;
}

// Interfaces for cost over time
interface DailyCost {
  date: string;
  total_cost: number;
  completion_count: number;
}

// Summary statistics interface
export interface AgentSummary {
  total_runs: number;
  total_cost: number;
  avg_cost_per_run: number;
  avg_duration: number;
}

// Combined agent details interface
interface AgentDetails {
  last_completions: Completion[];
  daily_costs: DailyCost[];
  summary: AgentSummary;
  fetchedAt: string;
}

interface AgentStatsState {
  agentDetails: Map<string, AgentDetails>;
  isLoadingDetails: Map<string, boolean>;
  detailsErrors: Map<string, Error>;

  fetchAgentDetails: (agentId: string) => Promise<AgentDetails>;
}

export const useAgentStats = create<AgentStatsState>((set, get) => ({
  agentDetails: new Map(),
  isLoadingDetails: new Map(),
  detailsErrors: new Map(),

  fetchAgentDetails: async (agentId: string) => {
    if (get().isLoadingDetails.get(agentId) ?? false) {
      const existing = get().agentDetails.get(agentId);
      return (
        existing || {
          last_completions: [],
          daily_costs: [],
          summary: {
            total_runs: 0,
            total_cost: 0,
            avg_cost_per_run: 0,
            avg_duration: 0,
          },
          fetchedAt: new Date().toISOString(),
        }
      );
    }

    set(
      produce((state: AgentStatsState) => {
        state.isLoadingDetails.set(agentId, true);
        state.detailsErrors.delete(agentId);
      })
    );

    try {
      // Helper function to execute queries
      const executeQuery = async (query: string) => {
        const response = await apiFetch(
          `/v1/completions/query?query=${encodeURIComponent(query)}`,
          {
            method: "GET",
          }
        );

        if (!response.ok) {
          throw new Error(
            `Query failed: ${response.status} ${response.statusText}`
          );
        }

        return await response.json();
      };

      // Execute all queries in parallel for better performance
      const [completionsData, summaryData, dailyCostData] = await Promise.all([
        // 1. Fetch last 20 completions for display
        executeQuery(`
          SELECT id, agent_id, created_at, cost_usd, duration_seconds, version_model, input_messages, output_messages, output_error
          FROM completions 
          WHERE agent_id = '${agentId}' 
          ORDER BY created_at DESC 
          LIMIT 20
        `) as Promise<Completion[]>,

        // 2. Fetch summary statistics with proper aliases
        executeQuery(`
          SELECT 
            COUNT(*) as total_runs,
            COALESCE(SUM(cost_usd), 0) as total_cost,
            COALESCE(AVG(cost_usd), 0) as avg_cost_per_run,
            COALESCE(AVG(duration_seconds), 0) as avg_duration
          FROM completions 
          WHERE agent_id = '${agentId}'
        `) as Promise<Array<AgentSummary>>,

        // 3. Fetch daily costs for last 30 days (calculate date client-side)
        (() => {
          const thirtyDaysAgo = new Date();
          thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
          const dateString = thirtyDaysAgo.toISOString().split("T")[0];
          return executeQuery(`
            SELECT created_at, cost_usd
            FROM completions 
            WHERE agent_id = '${agentId}' 
              AND created_at >= '${dateString}'
            ORDER BY created_at ASC
          `);
        })() as Promise<Array<{ created_at: string; cost_usd: number }>>,
      ]);

      const summary: AgentSummary = summaryData[0] || {
        total_runs: 0,
        total_cost: 0,
        avg_cost_per_run: 0,
        avg_duration: 0,
      };

      // Process daily costs (group by date client-side)
      const dailyGroups = new Map<
        string,
        { total_cost: number; completion_count: number }
      >();
      dailyCostData.forEach((item) => {
        const date = item.created_at.split("T")[0];
        const existing = dailyGroups.get(date) || {
          total_cost: 0,
          completion_count: 0,
        };
        existing.total_cost += item.cost_usd || 0;
        existing.completion_count += 1;
        dailyGroups.set(date, existing);
      });

      const dailyCosts: DailyCost[] = Array.from(dailyGroups.entries())
        .map(([date, data]) => ({
          date,
          total_cost: data.total_cost,
          completion_count: data.completion_count,
        }))
        .sort((a, b) => a.date.localeCompare(b.date));

      const agentDetails: AgentDetails = {
        last_completions: completionsData || [],
        daily_costs: dailyCosts,
        summary: summary,
        fetchedAt: new Date().toISOString(),
      };

      set(
        produce((state: AgentStatsState) => {
          state.agentDetails.set(agentId, agentDetails);
          state.isLoadingDetails.set(agentId, false);
        })
      );

      return agentDetails;
    } catch (error) {
      console.error(`Failed to fetch agent details for ${agentId}:`, error);

      set(
        produce((state: AgentStatsState) => {
          state.detailsErrors.set(agentId, error as Error);
          state.isLoadingDetails.set(agentId, false);
        })
      );

      return {
        last_completions: [],
        daily_costs: [],
        summary: {
          total_runs: 0,
          total_cost: 0,
          avg_cost_per_run: 0,
          avg_duration: 0,
        },
        fetchedAt: new Date().toISOString(),
      };
    }
  },
}));

export const useOrFetchAgentDetails = (agentId: string | undefined) => {
  const fetchAgentDetails = useAgentStats((state) => state.fetchAgentDetails);
  const agentDetails = useAgentStats((state) =>
    agentId ? state.agentDetails.get(agentId) : undefined
  );

  const isLoading = useAgentStats((state) =>
    agentId ? (state.isLoadingDetails.get(agentId) ?? false) : false
  );

  const error = useAgentStats((state) =>
    agentId ? state.detailsErrors.get(agentId) : undefined
  );

  const agentDetailsRef = useRef(agentDetails);
  agentDetailsRef.current = agentDetails;

  const update = useCallback(() => {
    if (agentId) {
      fetchAgentDetails(agentId);
    }
  }, [fetchAgentDetails, agentId]);

  useEffect(() => {
    if (!agentDetailsRef.current && agentId) {
      fetchAgentDetails(agentId);
    }
  }, [fetchAgentDetails, agentId]);

  return {
    details: agentDetails,
    isLoading,
    error,
    update,
  };
};
