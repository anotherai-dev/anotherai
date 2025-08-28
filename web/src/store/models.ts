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

    set({ isLoading: true, error: null });

    try {
      const response = await apiFetch("/v1/models");
      const models: Model[] = await response.json();
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
    }
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
    fetchModels();
  }, [fetchModels]);

  return {
    models,
    isLoading,
    error,
    getModelById,
  };
}
