import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef, useState } from "react";
import { create } from "zustand";
import { Deployment, DeploymentUpdate, Version } from "@/types/models";

enableMapSet();

// Mock data
const mockVersions: Version[] = [
  {
    id: "v1.0",
    model: "gpt-4o",
    temperature: 0.7,
    top_p: 1.0,
    prompt: [
      {
        role: "system",
        content: "You are a helpful AI assistant for customer support.",
      },
    ],
  },
  {
    id: "v2.1",
    model: "claude-3-5-sonnet-20241022",
    temperature: 0.5,
    top_p: 0.9,
    prompt: [
      {
        role: "system",
        content: "You are an expert data analyst. Analyze the provided data and give insights.",
      },
    ],
  },
  {
    id: "v1.5",
    model: "gpt-4o-mini",
    temperature: 1.0,
    top_p: 1.0,
    prompt: [
      {
        role: "system",
        content: "You are a creative writing assistant. Help users craft compelling stories.",
      },
    ],
  },
];

const mockDeployments: Deployment[] = [
  {
    id: "customer-support-prod",
    agent_id: "customer-support-agent",
    version: mockVersions[0],
    created_at: "2024-01-15T10:30:00Z",
    metadata: {
      environment: "production",
      team: "customer-success",
    },
  },
  {
    id: "data-analyzer-staging",
    agent_id: "data-analyzer",
    version: mockVersions[1],
    created_at: "2024-01-20T14:22:00Z",
    metadata: {
      environment: "staging",
      team: "data-science",
    },
  },
  {
    id: "creative-writer-dev",
    agent_id: "creative-writer",
    version: mockVersions[2],
    created_at: "2024-01-25T09:15:00Z",
    metadata: {
      environment: "development",
      team: "content",
    },
  },
  {
    id: "customer-support-staging",
    agent_id: "customer-support-agent",
    version: { ...mockVersions[0], id: "v1.1", temperature: 0.8 },
    created_at: "2024-01-18T16:45:00Z",
    metadata: {
      environment: "staging",
      team: "customer-success",
    },
  },
];

interface DeploymentsState {
  deployments: Deployment[];
  isLoading: boolean;
  error: Error | null;
  total: number;
  hasLoaded: boolean;
  nextPageToken?: string;
  previousPageToken?: string;

  fetchDeployments: (page?: number, pageSize?: number) => Promise<void>;
  createDeployment: (deployment: Deployment) => Promise<void>;
  updateDeployment: (deploymentId: string, update: DeploymentUpdate) => Promise<void>;
  deleteDeployment: (deploymentId: string) => Promise<void>;
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

let mockData = [...mockDeployments];

export const useMockedDeployments = create<DeploymentsState>((set, get) => ({
  ...initialState,

  fetchDeployments: async (page = 1, pageSize = 20) => {
    if (get().isLoading) return;

    set(
      produce((state: DeploymentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 500));

    try {
      const startIndex = (page - 1) * pageSize;
      const endIndex = startIndex + pageSize;
      const paginatedDeployments = mockData.slice(startIndex, endIndex);

      set(
        produce((state: DeploymentsState) => {
          state.deployments = paginatedDeployments;
          state.total = mockData.length;
          state.nextPageToken = endIndex < mockData.length ? `page-${page + 1}` : undefined;
          state.previousPageToken = page > 1 ? `page-${page - 1}` : undefined;
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

  createDeployment: async (deployment: Deployment) => {
    set(
      produce((state: DeploymentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300));

    try {
      const newDeployment: Deployment = {
        ...deployment,
        created_at: new Date().toISOString(),
      };

      mockData.unshift(newDeployment);

      set(
        produce((state: DeploymentsState) => {
          state.deployments.unshift(newDeployment);
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

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300));

    try {
      const deploymentIndex = mockData.findIndex((d) => d.id === deploymentId);
      if (deploymentIndex === -1) {
        throw new Error("Deployment not found");
      }

      const updatedDeployment: Deployment = {
        ...mockData[deploymentIndex],
        ...update,
        version: update.version || mockData[deploymentIndex].version,
        metadata: update.metadata || mockData[deploymentIndex].metadata,
      };

      mockData[deploymentIndex] = updatedDeployment;

      set(
        produce((state: DeploymentsState) => {
          const index = state.deployments.findIndex((d) => d.id === deploymentId);
          if (index !== -1) {
            state.deployments[index] = updatedDeployment;
          }
          state.isLoading = false;
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

  deleteDeployment: async (deploymentId: string) => {
    set(
      produce((state: DeploymentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300));

    try {
      const deploymentIndex = mockData.findIndex((d) => d.id === deploymentId);
      if (deploymentIndex === -1) {
        throw new Error("Deployment not found");
      }

      mockData.splice(deploymentIndex, 1);

      set(
        produce((state: DeploymentsState) => {
          state.deployments = state.deployments.filter((d) => d.id !== deploymentId);
          state.total -= 1;
          state.isLoading = false;
        })
      );
    } catch (error) {
      console.error("Failed to delete deployment:", error);
      set(
        produce((state: DeploymentsState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
    }
  },

  getDeployment: async (deploymentId: string): Promise<Deployment | null> => {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 200));

    try {
      const deployment = mockData.find((d) => d.id === deploymentId);
      return deployment || null;
    } catch (error) {
      console.error("Failed to fetch deployment:", error);
      return null;
    }
  },

  reset: () => {
    set(initialState);
    mockData = [...mockDeployments]; // Reset mock data too
  },
}));

export const useOrFetchMockedDeployments = () => {
  const fetchDeployments = useMockedDeployments((state) => state.fetchDeployments);
  const deployments = useMockedDeployments((state) => state.deployments);
  const isLoading = useMockedDeployments((state) => state.isLoading);
  const error = useMockedDeployments((state) => state.error);
  const total = useMockedDeployments((state) => state.total);
  const hasLoaded = useMockedDeployments((state) => state.hasLoaded);

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

export const useOrFetchMockedDeployment = (deploymentId: string) => {
  const getDeployment = useMockedDeployments((state) => state.getDeployment);

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
