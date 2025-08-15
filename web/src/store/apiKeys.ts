import { enableMapSet, produce } from "immer";
import { useCallback, useEffect } from "react";
import { create } from "zustand";
import { apiFetch } from "@/lib/apiFetch";
import { APIKey, APIKeyListResponse, CompleteAPIKey, CreateAPIKeyRequest } from "@/types/models";

enableMapSet();

interface APIKeysState {
  apiKeys: APIKey[];
  isLoading: boolean;
  error: Error | null;
  total: number;
  hasLoaded: boolean;

  fetchAPIKeys: () => Promise<void>;
  createAPIKey: (request: CreateAPIKeyRequest) => Promise<CompleteAPIKey | undefined>;
  deleteAPIKey: (keyId: string) => Promise<void>;
  clearError: () => void;
}

export const useAPIKeys = create<APIKeysState>((set, get) => ({
  apiKeys: [],
  isLoading: false,
  error: null,
  total: 0,
  hasLoaded: false,

  fetchAPIKeys: async () => {
    if (get().isLoading) return;

    set(
      produce((state: APIKeysState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const response = await apiFetch("/v1/organization/keys", {
        method: "GET",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data: APIKeyListResponse = await response.json();

      set(
        produce((state: APIKeysState) => {
          state.apiKeys = data.items;
          state.total = data.total;
          state.isLoading = false;
          state.hasLoaded = true;
          state.error = null;
        })
      );
    } catch (error) {
      set(
        produce((state: APIKeysState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
    }
  },

  createAPIKey: async (request: CreateAPIKeyRequest) => {
    set(
      produce((state: APIKeysState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const response = await apiFetch("/v1/organization/keys", {
        method: "POST",
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const newAPIKey: CompleteAPIKey = await response.json();

      set(
        produce((state: APIKeysState) => {
          // Add the new API key to the list (without the full key)
          const apiKeyWithoutFullKey: APIKey = {
            id: newAPIKey.id,
            name: newAPIKey.name,
            partial_key: newAPIKey.partial_key,
            created_at: newAPIKey.created_at,
            last_used_at: newAPIKey.last_used_at,
            created_by: newAPIKey.created_by,
          };
          state.apiKeys.unshift(apiKeyWithoutFullKey);
          state.total += 1;
          state.isLoading = false;
          state.error = null;
        })
      );

      return newAPIKey;
    } catch (error) {
      set(
        produce((state: APIKeysState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
      return undefined;
    }
  },

  deleteAPIKey: async (keyId: string) => {
    set(
      produce((state: APIKeysState) => {
        state.isLoading = true;
        state.error = null;
      })
    );

    try {
      const response = await apiFetch(`/v1/organization/keys/${keyId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      set(
        produce((state: APIKeysState) => {
          state.apiKeys = state.apiKeys.filter((key) => key.id !== keyId);
          state.total -= 1;
          state.isLoading = false;
          state.error = null;
        })
      );
    } catch (error) {
      set(
        produce((state: APIKeysState) => {
          state.isLoading = false;
          state.error = error instanceof Error ? error : new Error("Unknown error occurred");
        })
      );
    }
  },

  clearError: () => {
    set(
      produce((state: APIKeysState) => {
        state.error = null;
      })
    );
  },
}));

export const useOrFetchAPIKeys = () => {
  const fetchAPIKeys = useAPIKeys((state) => state.fetchAPIKeys);
  const apiKeys = useAPIKeys((state) => state.apiKeys);
  const isLoading = useAPIKeys((state) => state.isLoading);
  const error = useAPIKeys((state) => state.error);
  const total = useAPIKeys((state) => state.total);
  const hasLoaded = useAPIKeys((state) => state.hasLoaded);
  const createAPIKey = useAPIKeys((state) => state.createAPIKey);
  const deleteAPIKey = useAPIKeys((state) => state.deleteAPIKey);
  const clearError = useAPIKeys((state) => state.clearError);

  const update = useCallback(() => {
    fetchAPIKeys();
  }, [fetchAPIKeys]);

  useEffect(() => {
    if (!hasLoaded) {
      fetchAPIKeys();
    }
  }, [fetchAPIKeys, hasLoaded]);

  return {
    apiKeys,
    isLoading,
    error,
    total,
    hasLoaded,
    createAPIKey,
    deleteAPIKey,
    clearError,
    update,
  };
};
