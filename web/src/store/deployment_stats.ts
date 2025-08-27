import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";

enableMapSet();

interface DeploymentStats {
  completions_last_7_days: number;
  total_cost: number;
  active: boolean;
  last_completion_date: string | null;
}

interface DeploymentStatsResult {
  deployment_id: string;
  completions_last_7_days: number;
  total_cost: number;
  active: boolean;
  last_completion_date: string | null;
  fetchedAt: string;
}

interface DeploymentStatsState {
  deploymentStats: Map<string, DeploymentStatsResult>;
  isLoadingStats: Map<string, boolean>;
  statsErrors: Map<string, Error>;

  fetchDeploymentStats: (deploymentId: string) => Promise<DeploymentStats>;
  fetchMultipleDeploymentStats: (deploymentIds: string[]) => Promise<Map<string, DeploymentStats>>;
}

export const useDeploymentStats = create<DeploymentStatsState>((set, get) => ({
  deploymentStats: new Map(),
  isLoadingStats: new Map(),
  statsErrors: new Map(),

  fetchDeploymentStats: async (deploymentId: string) => {
    if (get().isLoadingStats.get(deploymentId) ?? false) {
      const existing = get().deploymentStats.get(deploymentId);
      return existing
        ? {
            completions_last_7_days: existing.completions_last_7_days,
            total_cost: existing.total_cost,
            active: existing.active,
            last_completion_date: existing.last_completion_date,
          }
        : {
            completions_last_7_days: 0,
            total_cost: 0,
            active: false,
            last_completion_date: null,
          };
    }

    set(
      produce((state: DeploymentStatsState) => {
        state.isLoadingStats.set(deploymentId, true);
        state.statsErrors.delete(deploymentId);
      })
    );

    try {
      // Query completions where metadata contains anotherai/deployment_id for last 7 days
      const query = `
        SELECT
          COUNT(*) as total_completions,
          COALESCE(SUM(cost_usd), 0) as total_cost,
          MAX(created_at) as last_completion
        FROM completions
        WHERE metadata['anotherai/deployment_id'] = '${deploymentId}'
          AND created_at >= subtractDays(now(), 7)
      `;

      const response = await apiFetch(`/v1/completions/query?query=${encodeURIComponent(query)}`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error(
          `Failed to fetch stats for deployment ${deploymentId}: ${response.status} ${response.statusText}`
        );
      }

      const statsData = (await response.json()) as {
        total_completions: number;
        total_cost: number;
        last_completion: string | null;
      }[];

      const stats = statsData[0] || {
        total_completions: 0,
        total_cost: 0,
        last_completion: null,
      };

      // Calculate if deployment is active (within 3 days)
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const isActive = stats.last_completion ? new Date(stats.last_completion) > threeDaysAgo : false;

      const deploymentStatsResult: DeploymentStatsResult = {
        deployment_id: deploymentId,
        completions_last_7_days: stats.total_completions || 0,
        total_cost: stats.total_cost || 0,
        active: isActive,
        last_completion_date: stats.last_completion,
        fetchedAt: new Date().toISOString(),
      };

      set(
        produce((state: DeploymentStatsState) => {
          state.deploymentStats.set(deploymentId, deploymentStatsResult);
          state.isLoadingStats.set(deploymentId, false);
        })
      );

      return {
        completions_last_7_days: deploymentStatsResult.completions_last_7_days,
        total_cost: deploymentStatsResult.total_cost,
        active: deploymentStatsResult.active,
        last_completion_date: deploymentStatsResult.last_completion_date,
      };
    } catch (error) {
      console.error(`Failed to fetch stats for deployment ${deploymentId}:`, error);

      set(
        produce((state: DeploymentStatsState) => {
          state.statsErrors.set(deploymentId, error as Error);
          state.isLoadingStats.set(deploymentId, false);
        })
      );

      return {
        completions_last_7_days: 0,
        total_cost: 0,
        active: false,
        last_completion_date: null,
      };
    }
  },

  fetchMultipleDeploymentStats: async (deploymentIds: string[]) => {
    if (deploymentIds.length === 0) {
      return new Map<string, DeploymentStats>();
    }

    // Mark all deployments as loading
    set(
      produce((state: DeploymentStatsState) => {
        deploymentIds.forEach((deploymentId) => {
          state.isLoadingStats.set(deploymentId, true);
          state.statsErrors.delete(deploymentId);
        });
      })
    );

    try {
      // Create IN clause with properly quoted deployment IDs
      const deploymentIdsString = deploymentIds.map((id) => `'${id}'`).join(", ");

      // Single comprehensive query for all deployments (last 7 days only)
      const query = `
        SELECT
          metadata['anotherai/deployment_id'] as deployment_id,
          COUNT(*) as total_completions,
          COALESCE(SUM(cost_usd), 0) as total_cost,
          MAX(created_at) as last_completion
        FROM completions
        WHERE metadata['anotherai/deployment_id'] IN (${deploymentIdsString})
          AND created_at >= subtractDays(now(), 7)
        GROUP BY metadata['anotherai/deployment_id']
      `;

      const response = await apiFetch(`/v1/completions/query?query=${encodeURIComponent(query)}`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch stats for multiple deployments: ${response.status} ${response.statusText}`);
      }

      const statsData = (await response.json()) as {
        deployment_id: string;
        total_completions: number;
        total_cost: number;
        last_completion: string | null;
      }[];

      // Calculate the date 3 days ago for active status check
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const statsMap = new Map<string, DeploymentStats>();

      // Process results and create map
      statsData.forEach((row) => {
        const isActive = row.last_completion ? new Date(row.last_completion) > threeDaysAgo : false;

        const deploymentStatsResult: DeploymentStatsResult = {
          deployment_id: row.deployment_id,
          completions_last_7_days: row.total_completions || 0,
          total_cost: row.total_cost || 0,
          active: isActive,
          last_completion_date: row.last_completion,
          fetchedAt: new Date().toISOString(),
        };

        // Store in state
        set(
          produce((state: DeploymentStatsState) => {
            state.deploymentStats.set(row.deployment_id, deploymentStatsResult);
            state.isLoadingStats.set(row.deployment_id, false);
          })
        );

        // Add to return map
        statsMap.set(row.deployment_id, {
          completions_last_7_days: deploymentStatsResult.completions_last_7_days,
          total_cost: deploymentStatsResult.total_cost,
          active: deploymentStatsResult.active,
          last_completion_date: deploymentStatsResult.last_completion_date,
        });
      });

      // For deployments not in the result (no completions in last 7 days), set them to 0
      deploymentIds.forEach((deploymentId) => {
        if (!statsMap.has(deploymentId)) {
          const deploymentStatsResult: DeploymentStatsResult = {
            deployment_id: deploymentId,
            completions_last_7_days: 0,
            total_cost: 0,
            active: false,
            last_completion_date: null,
            fetchedAt: new Date().toISOString(),
          };

          set(
            produce((state: DeploymentStatsState) => {
              state.deploymentStats.set(deploymentId, deploymentStatsResult);
              state.isLoadingStats.set(deploymentId, false);
            })
          );

          statsMap.set(deploymentId, {
            completions_last_7_days: 0,
            total_cost: 0,
            active: false,
            last_completion_date: null,
          });
        }
      });

      return statsMap;
    } catch (error) {
      console.error("Failed to fetch stats for multiple deployments:", error);

      // Mark all deployments as not loading and set error
      set(
        produce((state: DeploymentStatsState) => {
          deploymentIds.forEach((deploymentId) => {
            state.statsErrors.set(deploymentId, error as Error);
            state.isLoadingStats.set(deploymentId, false);
          });
        })
      );

      // Return empty stats for all deployments
      const statsMap = new Map<string, DeploymentStats>();
      deploymentIds.forEach((deploymentId) => {
        statsMap.set(deploymentId, {
          completions_last_7_days: 0,
          total_cost: 0,
          active: false,
          last_completion_date: null,
        });
      });
      return statsMap;
    }
  },
}));

export const useOrFetchDeploymentStats = (deploymentId: string | undefined) => {
  const fetchDeploymentStats = useDeploymentStats((state) => state.fetchDeploymentStats);
  const deploymentStats = useDeploymentStats((state) =>
    deploymentId ? state.deploymentStats.get(deploymentId) : undefined
  );

  const isLoading = useDeploymentStats((state) =>
    deploymentId ? (state.isLoadingStats.get(deploymentId) ?? false) : false
  );

  const error = useDeploymentStats((state) => (deploymentId ? state.statsErrors.get(deploymentId) : undefined));

  const deploymentStatsRef = useRef(deploymentStats);
  deploymentStatsRef.current = deploymentStats;

  const update = useCallback(() => {
    if (deploymentId) {
      fetchDeploymentStats(deploymentId);
    }
  }, [fetchDeploymentStats, deploymentId]);

  useEffect(() => {
    if (!deploymentStatsRef.current && deploymentId) {
      fetchDeploymentStats(deploymentId);
    }
  }, [fetchDeploymentStats, deploymentId]);

  return {
    stats: deploymentStats
      ? {
          completions_last_7_days: deploymentStats.completions_last_7_days,
          total_cost: deploymentStats.total_cost,
          active: deploymentStats.active,
          last_completion_date: deploymentStats.last_completion_date,
        }
      : undefined,
    isLoading,
    error,
    update,
  };
};

export const useOrFetchMultipleDeploymentStats = (deploymentIds: string[]) => {
  const fetchMultipleDeploymentStats = useDeploymentStats((state) => state.fetchMultipleDeploymentStats);
  const deploymentStats = useDeploymentStats((state) => state.deploymentStats);

  const allStats = new Map<string, DeploymentStats>();
  const anyLoading = deploymentIds.some((id) => useDeploymentStats.getState().isLoadingStats.get(id) ?? false);

  deploymentIds.forEach((deploymentId) => {
    const stats = deploymentStats.get(deploymentId);
    if (stats) {
      allStats.set(deploymentId, {
        completions_last_7_days: stats.completions_last_7_days,
        total_cost: stats.total_cost,
        active: stats.active,
        last_completion_date: stats.last_completion_date,
      });
    }
  });

  const allStatsRef = useRef(allStats);
  allStatsRef.current = allStats;

  const update = useCallback(() => {
    if (deploymentIds.length > 0) {
      fetchMultipleDeploymentStats(deploymentIds);
    }
  }, [fetchMultipleDeploymentStats, deploymentIds]);

  useEffect(() => {
    // Check if we have stats for all deployments, if not fetch them
    const missingStats = deploymentIds.filter((id) => !allStatsRef.current.has(id));
    if (missingStats.length > 0) {
      fetchMultipleDeploymentStats(deploymentIds);
    }
  }, [fetchMultipleDeploymentStats, deploymentIds]);

  return {
    allStats,
    isLoading: anyLoading,
    update,
  };
};
