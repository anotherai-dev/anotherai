import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import { ExperimentListItem, ExperimentListResponse } from "@/types/models";

enableMapSet();

interface ExperimentsState {
  experiments: ExperimentListItem[];
  isLoading: boolean;
  error: Error | null;
  total: number;
  hasLoaded: boolean;
  currentPage: number;
  pageSize: number;
  nextPageToken?: string;
  previousPageToken?: string;

  fetchExperiments: (page?: number, pageSize?: number) => Promise<void>;
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
}

export const useExperiments = create<ExperimentsState>((set, get) => ({
  experiments: [],
  isLoading: false,
  error: null,
  total: 0,
  hasLoaded: false,
  currentPage: 1,
  pageSize: 20,
  nextPageToken: undefined,
  previousPageToken: undefined,

  fetchExperiments: async (page?: number, pageSize?: number) => {
    if (get().isLoading) return;

    const state = get();
    const targetPage = page ?? state.currentPage;
    const targetPageSize = pageSize ?? state.pageSize;
    const offset = (targetPage - 1) * targetPageSize;

    set(
      produce((state: ExperimentsState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const response = await apiFetch(`/v1/experiments?limit=${targetPageSize}&offset=${offset}`, {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch experiments: ${response.status} ${response.statusText}`);
      }

      const data: ExperimentListResponse = await response.json();

      // Sort experiments by creation date (most recent first)
      const sortedExperiments = data.items.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      set(
        produce((state: ExperimentsState) => {
          state.experiments = sortedExperiments;
          state.total = data.total;
          state.currentPage = targetPage;
          state.pageSize = targetPageSize;
          state.nextPageToken = data.next_page_token;
          state.previousPageToken = data.previous_page_token;
          state.isLoading = false;
          state.hasLoaded = true;
        })
      );
    } catch (error) {
      console.error("Failed to fetch experiments:", error);

      set(
        produce((state: ExperimentsState) => {
          state.error = error as Error;
          state.isLoading = false;
        })
      );
    }
  },

  setPage: (page: number) => {
    const state = get();
    if (page !== state.currentPage && page > 0) {
      state.fetchExperiments(page);
    }
  },

  setPageSize: (pageSize: number) => {
    const state = get();
    if (pageSize !== state.pageSize && pageSize > 0) {
      state.fetchExperiments(1, pageSize);
    }
  },
}));

export const useOrFetchExperiments = () => {
  const fetchExperiments = useExperiments((state) => state.fetchExperiments);
  const experiments = useExperiments((state) => state.experiments);
  const isLoading = useExperiments((state) => state.isLoading);
  const error = useExperiments((state) => state.error);
  const total = useExperiments((state) => state.total);
  const hasLoaded = useExperiments((state) => state.hasLoaded);
  const currentPage = useExperiments((state) => state.currentPage);
  const pageSize = useExperiments((state) => state.pageSize);
  const setPage = useExperiments((state) => state.setPage);
  const setPageSize = useExperiments((state) => state.setPageSize);

  const experimentsRef = useRef(experiments);
  experimentsRef.current = experiments;

  const update = useCallback(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  useEffect(() => {
    if (!hasLoaded) {
      fetchExperiments();
    }
  }, [fetchExperiments, hasLoaded]);

  return {
    experiments,
    isLoading,
    error,
    total,
    currentPage,
    pageSize,
    setPage,
    setPageSize,
    update,
  };
};
