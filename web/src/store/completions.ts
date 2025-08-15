import { enableMapSet, produce } from "immer";
import { useEffect } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";

enableMapSet();

interface CompletionsQueryResult {
  data: Record<string, unknown>[];
  query: string;
  executedAt: string;
}

interface CompletionsState {
  queryResults: Map<string, CompletionsQueryResult>;
  isLoadingQuery: Map<string, boolean>;
  queryErrors: Map<string, Error>;
  newestCompletionId: string | null;
  isLoadingNewest: boolean;
  newestError: Error | null;

  queryCompletions: (query: string) => Promise<Record<string, unknown>[]>;
  fetchNewestCompletionId: () => Promise<void>;
}

export const useCompletions = create<CompletionsState>((set, get) => ({
  queryResults: new Map(),
  isLoadingQuery: new Map(),
  queryErrors: new Map(),
  newestCompletionId: null,
  isLoadingNewest: false,
  newestError: null,

  queryCompletions: async (query: string) => {
    const queryKey = query.trim();
    if (get().isLoadingQuery.get(queryKey) ?? false) {
      return [];
    }

    set(
      produce((state: CompletionsState) => {
        state.isLoadingQuery.set(queryKey, true);
        state.queryErrors.delete(queryKey);
      })
    );

    try {
      const encodedQuery = encodeURIComponent(query);
      const response = await apiFetch(`/v1/completions/query?query=${encodedQuery}`, {
        method: "GET",
      });

      if (!response.ok) {
        console.error(
          `Failed to query completions: ${response.status} ${response.statusText}`
        );
        set(
          produce((state: CompletionsState) => {
            state.queryErrors.set(
              queryKey,
              new Error(`HTTP ${response.status}: ${response.statusText}`)
            );
            state.isLoadingQuery.set(queryKey, false);
          })
        );
        return [];
      }

      const completionsData: Record<string, unknown>[] = await response.json();

      const queryResult: CompletionsQueryResult = {
        data: completionsData,
        query,
        executedAt: new Date().toISOString(),
      };

      set(
        produce((state: CompletionsState) => {
          state.queryResults.set(queryKey, queryResult);
          state.isLoadingQuery.set(queryKey, false);
        })
      );

      return completionsData;
    } catch (error) {
      set(
        produce((state: CompletionsState) => {
          state.queryErrors.set(queryKey, error as Error);
          state.isLoadingQuery.set(queryKey, false);
        })
      );

      return [];
    }
  },

  fetchNewestCompletionId: async () => {
    if (get().isLoadingNewest) return;

    set(
      produce((state: CompletionsState) => {
        state.isLoadingNewest = true;
        state.newestError = null;
      })
    );

    try {
      const query =
        "SELECT id FROM completions ORDER BY created_at DESC LIMIT 1";
      const encodedQuery = encodeURIComponent(query);
      const response = await apiFetch(
        `/v1/completions/query?query=${encodedQuery}`,
        {
          method: "GET",
        }
      );

      if (!response.ok) {
        console.error(
          `Failed to fetch newest completion ID: ${response.status} ${response.statusText}`
        );
        set(
          produce((state: CompletionsState) => {
            state.newestCompletionId = null;
            state.isLoadingNewest = false;
            state.newestError = new Error(
              `HTTP ${response.status}: ${response.statusText}`
            );
          })
        );
        return;
      }

      const completionsData: Record<string, unknown>[] = await response.json();
      const newestCompletionId =
        completionsData.length > 0 ? (completionsData[0].id as string) : null;

      set(
        produce((state: CompletionsState) => {
          state.newestCompletionId = newestCompletionId;
          state.isLoadingNewest = false;
        })
      );
    } catch (error) {
      console.error("Failed to fetch newest completion:", error);

      set(
        produce((state: CompletionsState) => {
          state.newestCompletionId = null;
          state.newestError = error as Error;
          state.isLoadingNewest = false;
        })
      );
    }
  },
}));

export const useCompletionsQuery = (query: string | undefined) => {
  const queryCompletions = useCompletions((state) => state.queryCompletions);
  const queryKey = query?.trim();

  const queryResult = useCompletions((state) => (queryKey ? state.queryResults.get(queryKey) : undefined));

  const isLoading = useCompletions((state) => (queryKey ? (state.isLoadingQuery.get(queryKey) ?? false) : false));

  const error = useCompletions((state) => (queryKey ? state.queryErrors.get(queryKey) : undefined));

  useEffect(() => {
    if (queryKey) {
      queryCompletions(queryKey);
    }
  }, [queryCompletions, queryKey]);

  const data = queryResult?.data;

  return {
    data: data && data.length > 0 ? data : undefined,
    query: queryResult?.query,
    executedAt: queryResult?.executedAt,
    isLoading,
    error,
  };
};

export const useNewestCompletionId = () => {
  const fetchNewestCompletionId = useCompletions(
    (state) => state.fetchNewestCompletionId
  );
  const newestCompletionId = useCompletions(
    (state) => state.newestCompletionId
  );
  const isLoading = useCompletions((state) => state.isLoadingNewest);
  const error = useCompletions((state) => state.newestError);

  useEffect(() => {
    if (!newestCompletionId) {
      fetchNewestCompletionId();
    }
  }, [fetchNewestCompletionId, newestCompletionId]);

  return {
    newestCompletionId,
    isLoading,
    error,
    refresh: fetchNewestCompletionId,
  };
};
