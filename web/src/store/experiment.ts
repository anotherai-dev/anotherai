import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import { Experiment, ExperimentWithLookups, createExperimentWithLookups } from "@/types/models";

enableMapSet();

interface ExperimentState {
  experiments: Map<string, ExperimentWithLookups>;
  isLoadingExperiment: Map<string, boolean>;
  experimentErrors: Map<string, Error>;

  fetchExperiment: (experimentId: string) => Promise<void>;
}

export const useExperiment = create<ExperimentState>((set, get) => ({
  experiments: new Map(),
  isLoadingExperiment: new Map(),
  experimentErrors: new Map(),

  fetchExperiment: async (experimentId: string) => {
    if (get().isLoadingExperiment.get(experimentId) ?? false) return;

    set(
      produce((state: ExperimentState) => {
        state.isLoadingExperiment.set(experimentId, true);
        state.experimentErrors.delete(experimentId);
      })
    );

    try {
      const response = await apiFetch(`/v1/experiments/${experimentId}`, {
        method: "GET",
      });

      if (!response.ok) {
        set(
          produce((state: ExperimentState) => {
            state.experimentErrors.set(experimentId, new Error(`${response.status} ${response.statusText}`));
            state.isLoadingExperiment.set(experimentId, false);
          })
        );
        return;
      }

      const experimentData: Experiment = await response.json();
      const experimentWithLookups = createExperimentWithLookups(experimentData);

      set(
        produce((state: ExperimentState) => {
          state.experiments.set(experimentId, experimentWithLookups);
          state.isLoadingExperiment.set(experimentId, false);
        })
      );
    } catch (error) {
      console.error("Failed to fetch experiment:", error);

      set(
        produce((state: ExperimentState) => {
          state.experimentErrors.set(experimentId, error as Error);
          state.isLoadingExperiment.set(experimentId, false);
        })
      );
    }
  },
}));

export const useOrFetchExperiment = (experimentId: string | undefined) => {
  const fetchExperiment = useExperiment((state) => state.fetchExperiment);
  const experiment = useExperiment((state) => (experimentId ? state.experiments.get(experimentId) : undefined));

  const isLoading = useExperiment((state) =>
    experimentId ? (state.isLoadingExperiment.get(experimentId) ?? false) : false
  );

  const error = useExperiment((state) => (experimentId ? state.experimentErrors.get(experimentId) : undefined));

  const experimentRef = useRef(experiment);
  experimentRef.current = experiment;

  const update = useCallback(() => {
    if (experimentId) {
      fetchExperiment(experimentId);
    }
  }, [fetchExperiment, experimentId]);

  useEffect(() => {
    if (!experimentRef.current && experimentId) {
      fetchExperiment(experimentId);
    }
  }, [fetchExperiment, experimentId]);

  return {
    experiment,
    isLoading,
    error,
    update,
  };
};
