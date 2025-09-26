import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { createErrorFromResponse } from "@/lib/apiError";
import { apiFetch } from "@/lib/apiFetch";
import { Completion } from "@/types/models";

enableMapSet();

interface CompletionState {
  completions: Map<string, Completion>;
  isLoadingCompletion: Map<string, boolean>;
  completionErrors: Map<string, Error>;

  fetchCompletion: (completionId: string) => Promise<void>;
}

export const useCompletion = create<CompletionState>((set, get) => ({
  completions: new Map(),
  isLoadingCompletion: new Map(),
  completionErrors: new Map(),

  fetchCompletion: async (completionId: string) => {
    if (get().isLoadingCompletion.get(completionId) ?? false) return;

    set(
      produce((state: CompletionState) => {
        state.isLoadingCompletion.set(completionId, true);
        state.completionErrors.delete(completionId);
      })
    );

    try {
      const response = await apiFetch(`/v1/completions/${completionId}`, {
        method: "GET",
      });

      if (!response.ok) {
        throw await createErrorFromResponse(response);
      }

      const completionData: Completion = await response.json();

      set(
        produce((state: CompletionState) => {
          state.completions.set(completionId, completionData);
          state.isLoadingCompletion.set(completionId, false);
        })
      );
    } catch (error) {
      // Skip console logging for API errors to reduce noise
      const errorObj = error as Error & { isApiError?: boolean };
      if (!errorObj.isApiError) {
        console.error("Failed to fetch completion:", error);
      }

      set(
        produce((state: CompletionState) => {
          state.completionErrors.set(completionId, error as Error);
          state.isLoadingCompletion.set(completionId, false);
        })
      );
    }
  },
}));

export const useOrFetchCompletion = (completionId: string | undefined) => {
  const fetchCompletion = useCompletion((state) => state.fetchCompletion);
  const completion = useCompletion((state) => (completionId ? state.completions.get(completionId) : undefined));

  const isLoading = useCompletion((state) =>
    completionId ? (state.isLoadingCompletion.get(completionId) ?? false) : false
  );

  const error = useCompletion((state) => (completionId ? state.completionErrors.get(completionId) : undefined));

  const completionRef = useRef(completion);
  completionRef.current = completion;

  const update = useCallback(() => {
    if (completionId) {
      fetchCompletion(completionId);
    }
  }, [fetchCompletion, completionId]);

  useEffect(() => {
    if (!completionRef.current && completionId) {
      fetchCompletion(completionId);
    }
  }, [fetchCompletion, completionId]);

  return {
    completion,
    isLoading,
    error,
    update,
  };
};
