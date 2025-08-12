import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useRef } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import { Annotation, Page } from "@/types/models";

enableMapSet();

interface AnnotationFilters {
  experiment_id?: string;
  completion_id?: string;
  since?: string;
  limit?: number;
}

interface AnnotationsState {
  annotations: Map<string, Annotation[]>; // Key: filter hash, Value: annotations
  isLoading: Map<string, boolean>;
  errors: Map<string, Error>;
  hasFetched: Map<string, boolean>; // Track which filters have been attempted

  // CRUD operations
  fetchAnnotations: (filters?: AnnotationFilters) => Promise<void>;
  addAnnotations: (annotations: Annotation[]) => Promise<boolean>;
  deleteAnnotation: (annotationId: string) => Promise<boolean>;

  // Utility methods
  clearCache: () => void;
  getFilterKey: (filters?: AnnotationFilters) => string;
}

// Helper function to create a consistent key for caching
const createFilterKey = (filters?: AnnotationFilters): string => {
  if (!filters) return "all";

  const parts: string[] = [];
  if (filters.experiment_id) parts.push(`exp:${filters.experiment_id}`);
  if (filters.completion_id) parts.push(`comp:${filters.completion_id}`);
  if (filters.since) parts.push(`since:${filters.since}`);
  if (filters.limit) parts.push(`limit:${filters.limit}`);

  return parts.join("|") || "all";
};

// Create a constant empty array to avoid re-renders
const EMPTY_ANNOTATIONS: Annotation[] = [];

export const useAnnotations = create<AnnotationsState>((set, get) => ({
  annotations: new Map(),
  isLoading: new Map(),
  errors: new Map(),
  hasFetched: new Map(),

  getFilterKey: createFilterKey,

  fetchAnnotations: async (filters?: AnnotationFilters) => {
    const filterKey = createFilterKey(filters);

    if (get().isLoading.get(filterKey) ?? false) return;

    set(
      produce((state: AnnotationsState) => {
        state.isLoading.set(filterKey, true);
        state.errors.delete(filterKey);
      })
    );

    try {
      const params = new URLSearchParams();
      if (filters?.experiment_id)
        params.append("experiment_id", filters.experiment_id);
      if (filters?.completion_id)
        params.append("completion_id", filters.completion_id);
      if (filters?.since) params.append("since", filters.since);
      if (filters?.limit) params.append("limit", filters.limit.toString());

      const url = `/v1/annotations${params.toString() ? `?${params.toString()}` : ""}`;

      const response = await apiFetch(url, {
        method: "GET",
      });

      if (!response.ok) {
        set(
          produce((state: AnnotationsState) => {
            state.annotations.set(filterKey, EMPTY_ANNOTATIONS);
            state.isLoading.set(filterKey, false);
            state.hasFetched.set(filterKey, true);
          })
        );
        return;
      }

      const data: Page<Annotation> = await response.json();

      set(
        produce((state: AnnotationsState) => {
          state.annotations.set(filterKey, data.items);
          state.isLoading.set(filterKey, false);
          state.hasFetched.set(filterKey, true);
        })
      );
    } catch (error) {
      console.error("Failed to fetch annotations:", error);

      set(
        produce((state: AnnotationsState) => {
          state.errors.set(filterKey, error as Error);
          state.isLoading.set(filterKey, false);
          state.hasFetched.set(filterKey, true);
        })
      );
    }
  },

  addAnnotations: async (annotations: Annotation[]): Promise<boolean> => {
    try {
      const response = await apiFetch("/v1/annotations", {
        method: "POST",
        body: JSON.stringify(annotations),
      });

      if (!response.ok) {
        console.error(
          `Failed to add annotations: ${response.status} ${response.statusText}`
        );
        return false;
      }

      // Clear cache to force refetch
      set(
        produce((state: AnnotationsState) => {
          state.annotations.clear();
          state.isLoading.clear();
          state.errors.clear();
          state.hasFetched.clear();
        })
      );

      return true;
    } catch (error) {
      console.error("Failed to add annotations:", error);
      return false;
    }
  },

  deleteAnnotation: async (annotationId: string): Promise<boolean> => {
    try {
      const response = await apiFetch(`/v1/annotations/${annotationId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        console.error(
          `Failed to delete annotation: ${response.status} ${response.statusText}`
        );
        return false;
      }

      // Remove annotation from all cached results
      set(
        produce((state: AnnotationsState) => {
          state.annotations.forEach((annotationList, key) => {
            const filtered = annotationList.filter(
              (annotation) => annotation.id !== annotationId
            );
            state.annotations.set(key, filtered);
          });
        })
      );

      return true;
    } catch (error) {
      console.error("Failed to delete annotation:", error);
      return false;
    }
  },

  clearCache: () => {
    set(
      produce((state: AnnotationsState) => {
        state.annotations.clear();
        state.isLoading.clear();
        state.errors.clear();
        state.hasFetched.clear();
      })
    );
  },
}));

// Hook for fetching annotations with filters
export const useOrFetchAnnotations = (filters?: AnnotationFilters) => {
  const fetchAnnotations = useAnnotations((state) => state.fetchAnnotations);
  const getFilterKey = useAnnotations((state) => state.getFilterKey);
  const clearCache = useAnnotations((state) => state.clearCache);

  const filterKey = getFilterKey(filters);

  const annotations = useAnnotations((state) => {
    const result = state.annotations.get(filterKey);
    return result ?? EMPTY_ANNOTATIONS;
  });
  const isLoading = useAnnotations(
    (state) => state.isLoading.get(filterKey) ?? false
  );
  const error = useAnnotations((state) => state.errors.get(filterKey));
  const hasFetched = useAnnotations(
    (state) => state.hasFetched.get(filterKey) ?? false
  );

  const annotationsRef = useRef(annotations);
  annotationsRef.current = annotations;

  const update = useCallback(() => {
    fetchAnnotations(filters);
  }, [fetchAnnotations, filters]);

  const refresh = useCallback(() => {
    clearCache();
    fetchAnnotations(filters);
  }, [clearCache, fetchAnnotations, filters]);

  useEffect(() => {
    if (!hasFetched && !isLoading && !error) {
      fetchAnnotations(filters);
    }
  }, [fetchAnnotations, filters, isLoading, error, hasFetched]);

  return {
    annotations,
    isLoading,
    error,
    update,
    refresh,
  };
};

// Hook for annotation CRUD operations
export const useAnnotationActions = () => {
  const addAnnotations = useAnnotations((state) => state.addAnnotations);
  const deleteAnnotation = useAnnotations((state) => state.deleteAnnotation);
  const clearCache = useAnnotations((state) => state.clearCache);

  return {
    addAnnotations,
    deleteAnnotation,
    clearCache,
  };
};
