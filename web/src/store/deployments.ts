import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef, useState } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import { Deployment, DeploymentCreate, DeploymentListResponse, DeploymentUpdate } from "@/types/models";

enableMapSet();

interface DeploymentsState {
  deployments: Deployment[];
  isLoading: boolean;
  error: Error | null;
  total: number;
  hasLoaded: boolean;
  nextPageToken?: string;
  previousPageToken?: string;

  fetchDeployments: (agentId?: string, includeArchived?: boolean, limit?: number, pageToken?: string) => Promise<void>;
  createDeployment: (deployment: DeploymentCreate) => Promise<void>;
  updateDeployment: (deploymentId: string, update: DeploymentUpdate) => Promise<void>;
  archiveDeployment: (deploymentId: string) => Promise<void>;
  getDeployment: (deploymentId: string) => Promise<Deployment | null>;
  reset: () => void;
}

const initialState = {
  deployments: [],
  isLoading: false,
  error: null,
  total: 0,
  hasLoaded: false,
  nextPageToken: undefined,
  previousPageToken: undefined,
};

export const useDeployments = create<DeploymentsState>((set, get) => ({
  ...initialState,

  fetchDeployments: async (agentId?: string, includeArchived = false, limit = 20, pageToken?: string) => {
    if (get().isLoading) return;

    set(
      produce((state: DeploymentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        include_archived: includeArchived.toString(),
      });

      if (agentId) {
        params.set("agent_id", agentId);
      }

      if (pageToken) {
        params.set("page_token", pageToken);
      }

      const response = await apiFetch(`/v1/deployments?${params}`, {
        method: "GET",
      });

      if (!response.ok) {
        console.error(`Failed to fetch deployments: ${response.status} ${response.statusText}`);
        set(
          produce((state: DeploymentsState) => {
            state.isLoading = false;
            state.error = new Error(`Failed to fetch deployments: ${response.status} ${response.statusText}`);
          })
        );
        return;
      }

      const data: DeploymentListResponse = await response.json();

      set(
        produce((state: DeploymentsState) => {
          state.deployments = data.items;
          state.total = data.total;
          state.nextPageToken = data.next_page_token;
          state.previousPageToken = data.previous_page_token;
          state.isLoading = false;
          state.hasLoaded = true;
          state.error = null;
        })
      );
    } catch (error) {
      console.error("Failed to fetch deployments:", error);
      set(
        produce((state: DeploymentsState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
    }
  },

  createDeployment: async (deployment: DeploymentCreate) => {
    set(
      produce((state: DeploymentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const response = await apiFetch("/v1/deployments", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(deployment),
      });

      if (!response.ok) {
        console.error(`Failed to create deployment: ${response.status} ${response.statusText}`);
        set(
          produce((state: DeploymentsState) => {
            state.isLoading = false;
            state.error = new Error(`Failed to create deployment: ${response.status} ${response.statusText}`);
          })
        );
        return;
      }

      const createdDeployment: Deployment = await response.json();

      set(
        produce((state: DeploymentsState) => {
          state.deployments.unshift(createdDeployment);
          state.total += 1;
          state.isLoading = false;
        })
      );
    } catch (error) {
      console.error("Failed to create deployment:", error);
      set(
        produce((state: DeploymentsState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
    }
  },

  updateDeployment: async (deploymentId: string, update: DeploymentUpdate) => {
    set(
      produce((state: DeploymentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const patchUrl = `/v1/deployments/${encodeURIComponent(deploymentId)}`;

      const response = await apiFetch(patchUrl, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(update),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`PATCH request failed: ${errorText}`);
      }

      if (response.ok) {
        const updatedDeployment: Deployment = await response.json();

        set(
          produce((state: DeploymentsState) => {
            const index = state.deployments.findIndex((d) => d.id === deploymentId);
            if (index !== -1) {
              state.deployments[index] = updatedDeployment;
            }
            state.isLoading = false;
          })
        );
        return;
      }

      // If we get here, update failed
      console.error(`Failed to update deployment: ${response.status} ${response.statusText}`);
      set(
        produce((state: DeploymentsState) => {
          state.isLoading = false;
          state.error = new Error(`Failed to update deployment: ${response.status} ${response.statusText}`);
        })
      );
    } catch (error) {
      console.error("Failed to update deployment:", error);
      set(
        produce((state: DeploymentsState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
    }
  },

  archiveDeployment: async (deploymentId: string) => {
    set(
      produce((state: DeploymentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const response = await apiFetch(`/v1/deployments/${encodeURIComponent(deploymentId)}/archive`, {
        method: "POST",
      });

      if (!response.ok) {
        console.error(`Failed to archive deployment: ${response.status} ${response.statusText}`);
        set(
          produce((state: DeploymentsState) => {
            state.isLoading = false;
            state.error = new Error(`Failed to archive deployment: ${response.status} ${response.statusText}`);
          })
        );
        return;
      }

      set(
        produce((state: DeploymentsState) => {
          state.deployments = state.deployments.filter((d) => d.id !== deploymentId);
          state.total -= 1;
          state.isLoading = false;
        })
      );
    } catch (error) {
      console.error("Failed to archive deployment:", error);
      set(
        produce((state: DeploymentsState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
    }
  },

  getDeployment: async (deploymentId: string): Promise<Deployment | null> => {
    try {
      const response = await apiFetch(`/v1/deployments/${encodeURIComponent(deploymentId)}`, {
        method: "GET",
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        console.error(`Failed to fetch deployment: ${response.status} ${response.statusText}`);
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error("Failed to fetch deployment:", error);
      return null;
    }
  },

  reset: () => {
    set(initialState);
  },
}));

export const useOrFetchDeployments = () => {
  const fetchDeployments = useDeployments((state) => state.fetchDeployments);
  const deployments = useDeployments((state) => state.deployments);
  const isLoading = useDeployments((state) => state.isLoading);
  const error = useDeployments((state) => state.error);
  const total = useDeployments((state) => state.total);
  const hasLoaded = useDeployments((state) => state.hasLoaded);

  const deploymentsRef = useRef(deployments);
  deploymentsRef.current = deployments;

  const update = useCallback(() => {
    fetchDeployments();
  }, [fetchDeployments]);

  useEffect(() => {
    if (!hasLoaded) {
      fetchDeployments();
    }
  }, [fetchDeployments, hasLoaded]);

  return {
    deployments,
    isLoading,
    error,
    total,
    update,
  };
};

export const useOrFetchDeployment = (deploymentId: string) => {
  const getDeployment = useDeployments((state) => state.getDeployment);

  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchDeployment = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await getDeployment(deploymentId);
      setDeployment(result);
    } catch (err) {
      console.error("Failed to fetch deployment:", err);
      setError(err instanceof Error ? err : new Error("Unknown error occurred"));
    } finally {
      setIsLoading(false);
    }
  }, [deploymentId, getDeployment]);

  useEffect(() => {
    if (deploymentId) {
      fetchDeployment();
    }
  }, [deploymentId, fetchDeployment]);

  return {
    deployment,
    isLoading,
    error,
    refetch: fetchDeployment,
  };
};
