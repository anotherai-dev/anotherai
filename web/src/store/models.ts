import { useEffect } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import { Model } from "@/types/models";

interface ModelsState {
  models: Model[];
  modelsById: Map<string, Model>;
  isLoading: boolean;
  error: string | null;
  fetchModels: () => Promise<void>;
  getModelById: (id: string) => Model | undefined;
}

// Singleton promise to ensure only one fetch happens at a time
let fetchPromise: Promise<void> | null = null;

export const useModelsStore = create<ModelsState>((set, get) => ({
  models: [],
  modelsById: new Map(),
  isLoading: false,
  error: null,

  fetchModels: async () => {
    const state = get();

    if (state.models.length > 0) {
      // Already loaded, don't fetch again
      return;
    }

    if (fetchPromise) {
      // Already fetching, wait for the existing promise
      return fetchPromise;
    }

    // Start the fetch operation
    fetchPromise = (async () => {
      set({ isLoading: true, error: null });

      try {
        const response = await apiFetch("/v1/models");
        const result: { data: Model[] } = await response.json();
        const models = result.data;
        const modelsById = new Map(models.map((model) => [model.id, model]));

        set({
          models,
          modelsById,
          isLoading: false,
          error: null,
        });
      } catch (error) {
        console.error("Failed to fetch models:", error);
        set({
          isLoading: false,
          error: error instanceof Error ? error.message : "Failed to fetch models",
        });
      } finally {
        // Reset the promise so future calls can start a new fetch if needed
        fetchPromise = null;
      }
    })();

    return fetchPromise;
  },

  getModelById: (id: string) => {
    return get().modelsById.get(id);
  },
}));

/**
 * Hook that ensures models are loaded and provides model access
 * Only fetches models once when first component mounts
 */
export function useOrFetchModels() {
  const { models, isLoading, error, fetchModels, getModelById } = useModelsStore();

  useEffect(() => {
    // fetchModels now handles all the deduplication logic internally
    fetchModels();
  }, [fetchModels]);

  return {
    models,
    isLoading,
    error,
    getModelById,
  };
}
