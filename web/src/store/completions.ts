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

  queryCompletions: (query: string) => Promise<Record<string, unknown>[]>;
}

export const useCompletions = create<CompletionsState>((set, get) => ({
  queryResults: new Map(),
  isLoadingQuery: new Map(),
  queryErrors: new Map(),

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
      const response = await apiFetch(
        `/v1/completions/query?query=${encodedQuery}`,
        {
          method: "GET",
        }
      );

      if (!response.ok) {
        throw new Error(
          `Failed to query completions: ${response.status} ${response.statusText}`
        );
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
}));

export const useCompletionsQuery = (query: string | undefined) => {
  const queryCompletions = useCompletions((state) => state.queryCompletions);
  const queryKey = query?.trim();

  const queryResult = useCompletions((state) =>
    queryKey ? state.queryResults.get(queryKey) : undefined
  );

  const isLoading = useCompletions((state) =>
    queryKey ? (state.isLoadingQuery.get(queryKey) ?? false) : false
  );

  const error = useCompletions((state) =>
    queryKey ? state.queryErrors.get(queryKey) : undefined
  );

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
