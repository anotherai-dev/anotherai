import { enableMapSet, produce } from "immer";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { create } from "zustand";
import { useAuth } from "@/auth/components";
import { apiFetch } from "@/lib/apiFetch";
import {
  CreateViewRequest,
  CreateViewResponse,
  PatchViewFolderRequest,
  PatchViewRequest,
  View,
  ViewFolder,
  ViewListResponse,
} from "@/types/models";

enableMapSet();

interface ViewsState {
  viewFolders: ViewFolder[];
  viewFoldersMap: Map<string, ViewFolder>;
  viewsMap: Map<string, View>;
  isLoadingViewFolders: boolean;
  isLoadingView: Map<string, boolean>;
  viewFoldersError: Error | null;
  viewErrors: Map<string, Error>;
  total: number;
  hasLoaded: boolean;
  currentPage: number;
  pageSize: number;
  nextPageToken?: string;
  previousPageToken?: string;
  abortControllers: Map<string, AbortController>;

  // View folder operations
  fetchViewFolders: (page?: number, pageSize?: number) => Promise<void>;
  createViewFolder: (folder: Omit<ViewFolder, "id" | "views">) => Promise<ViewFolder | null>;
  patchViewFolder: (folderId: string, patch: PatchViewFolderRequest) => Promise<void>;
  deleteViewFolder: (folderId: string) => Promise<void>;

  // View operations
  fetchView: (viewId: string) => Promise<void>;
  createView: (view: CreateViewRequest) => Promise<CreateViewResponse | null>;
  patchView: (viewId: string, patch: PatchViewRequest) => Promise<View | null>;
  deleteView: (viewId: string) => Promise<void>;

  // Pagination
  setPage: (page: number) => void;
  setPageSize: (pageSize: number) => void;
}

export const useViews = create<ViewsState>((set, get) => ({
  viewFolders: [],
  viewFoldersMap: new Map(),
  viewsMap: new Map(),
  isLoadingViewFolders: false,
  isLoadingView: new Map(),
  viewFoldersError: null,
  viewErrors: new Map(),
  total: 0,
  hasLoaded: false,
  currentPage: 1,
  pageSize: 20,
  nextPageToken: undefined,
  previousPageToken: undefined,
  abortControllers: new Map(),

  fetchViewFolders: async (page?: number, pageSize?: number) => {
    if (get().isLoadingViewFolders) return;

    const state = get();
    const targetPage = page ?? state.currentPage;
    const targetPageSize = pageSize ?? state.pageSize;

    // Cancel any existing request
    const existingController = state.abortControllers.get("fetchViewFolders");
    if (existingController) {
      existingController.abort();
    }

    // Create new AbortController
    const abortController = new AbortController();

    set(
      produce((state: ViewsState) => {
        state.isLoadingViewFolders = true;
        state.viewFoldersError = null;
        state.abortControllers.set("fetchViewFolders", abortController);
      })
    );

    try {
      const response = await apiFetch("/v1/views", {
        method: "GET",
        signal: abortController.signal,
      });

      if (!response.ok) {
        console.error(`Failed to fetch view folders: ${response.status} ${response.statusText}`);
        set(
          produce((state: ViewsState) => {
            state.viewFoldersError = new Error(
              `Failed to fetch view folders: ${response.status} ${response.statusText}`
            );
            state.isLoadingViewFolders = false;
            state.abortControllers.delete("fetchViewFolders");
          })
        );
        return;
      }

      const data: ViewListResponse = await response.json();

      // Create maps for both folders and individual views
      const viewFoldersMap = new Map(data.items.map((folder) => [folder.id, folder]));
      const viewsMap = new Map<string, View>();

      data.items.forEach((folder) => {
        folder.views.forEach((view) => {
          viewsMap.set(view.id, view);
        });
      });

      set(
        produce((state: ViewsState) => {
          state.viewFolders = data.items;
          state.viewFoldersMap = viewFoldersMap;
          state.viewsMap = viewsMap;
          state.total = data.total;
          state.currentPage = targetPage;
          state.pageSize = targetPageSize;
          state.nextPageToken = data.next_page_token;
          state.previousPageToken = data.previous_page_token;
          state.isLoadingViewFolders = false;
          state.hasLoaded = true;
          state.abortControllers.delete("fetchViewFolders");
        })
      );
    } catch (error) {
      // Don't update state if request was aborted
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }

      console.error("Failed to fetch view folders:", error);

      set(
        produce((state: ViewsState) => {
          state.viewFoldersError = error as Error;
          state.isLoadingViewFolders = false;
          state.abortControllers.delete("fetchViewFolders");
        })
      );
    }
  },

  fetchView: async (viewId: string) => {
    if (get().isLoadingView.get(viewId) ?? false) return;

    const state = get();

    // Cancel any existing request for this view
    const existingController = state.abortControllers.get(`fetchView-${viewId}`);
    if (existingController) {
      existingController.abort();
    }

    // Create new AbortController
    const abortController = new AbortController();

    set(
      produce((state: ViewsState) => {
        state.isLoadingView.set(viewId, true);
        state.viewErrors.delete(viewId);
        state.abortControllers.set(`fetchView-${viewId}`, abortController);
      })
    );

    try {
      const response = await apiFetch(`/v1/views/${viewId}`, {
        method: "GET",
        signal: abortController.signal,
      });

      if (!response.ok) {
        console.error(`Failed to fetch view: ${response.status} ${response.statusText}`);
        set(
          produce((state: ViewsState) => {
            state.viewErrors.set(viewId, new Error(`Failed to fetch view: ${response.status} ${response.statusText}`));
            state.isLoadingView.set(viewId, false);
            state.abortControllers.delete(`fetchView-${viewId}`);
          })
        );
        return;
      }

      const view: View = await response.json();

      set(
        produce((state: ViewsState) => {
          state.viewsMap.set(viewId, view);
          state.isLoadingView.set(viewId, false);
          state.abortControllers.delete(`fetchView-${viewId}`);
        })
      );
    } catch (error) {
      // Don't update state if request was aborted
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }

      console.error("Failed to fetch view:", error);

      set(
        produce((state: ViewsState) => {
          state.viewErrors.set(viewId, error as Error);
          state.isLoadingView.set(viewId, false);
          state.abortControllers.delete(`fetchView-${viewId}`);
        })
      );
    }
  },

  createViewFolder: async (folder: Omit<ViewFolder, "id" | "views">) => {
    try {
      const response = await apiFetch("/v1/view-folders", {
        method: "POST",
        body: JSON.stringify(folder),
      });

      if (!response.ok) {
        throw new Error(`Failed to create view folder: ${response.status} ${response.statusText}`);
      }

      const createdFolder: ViewFolder = await response.json();

      // Optimistically add the folder for immediate UI feedback
      set(
        produce((state: ViewsState) => {
          state.viewFolders.push(createdFolder);
          state.viewFoldersMap.set(createdFolder.id, createdFolder);
        })
      );

      // Immediately refetch to get correct backend order/position
      get().fetchViewFolders();

      return createdFolder;
    } catch (error) {
      console.error("Failed to create view folder:", error);
      // Refetch on error to revert optimistic update
      get().fetchViewFolders();
      return null;
    }
  },

  patchViewFolder: async (folderId: string, patch: PatchViewFolderRequest) => {
    try {
      // Optimistically update the UI immediately
      if (patch.name !== undefined) {
        set(
          produce((state: ViewsState) => {
            // Update in viewFolders array
            const folderIndex = state.viewFolders.findIndex((f) => f.id === folderId);
            if (folderIndex !== -1) {
              state.viewFolders[folderIndex].name = patch.name ?? "";
            }

            // Update in viewFoldersMap
            const folder = state.viewFoldersMap.get(folderId);
            if (folder) {
              folder.name = patch.name ?? "";
            }
          })
        );
      }

      const response = await apiFetch(`/v1/view-folders/${folderId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });

      if (!response.ok) {
        throw new Error(`Failed to patch view folder: ${response.status} ${response.statusText}`);
      }

      // Immediately refetch to get correct backend order/position
      get().fetchViewFolders();
    } catch (error) {
      console.error("Failed to patch view folder:", error);
      // Refetch on error to revert optimistic update
      get().fetchViewFolders();
      throw error;
    }
  },

  deleteViewFolder: async (folderId: string) => {
    try {
      const response = await apiFetch(`/v1/view-folders/${folderId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`Failed to delete view folder: ${response.status} ${response.statusText}`);
      }

      set(
        produce((state: ViewsState) => {
          // Get folder reference BEFORE deleting it from the map
          const folder = state.viewFoldersMap.get(folderId);

          // Remove folder from arrays and maps
          state.viewFolders = state.viewFolders.filter((f) => f.id !== folderId);
          state.viewFoldersMap.delete(folderId);

          // Also remove all views from this folder
          if (folder) {
            folder.views.forEach((view) => {
              state.viewsMap.delete(view.id);
            });
          }
        })
      );
    } catch (error) {
      console.error("Failed to delete view folder:", error);
      throw error;
    }
  },

  createView: async (view: CreateViewRequest) => {
    try {
      const response = await apiFetch("/v1/views", {
        method: "POST",
        body: JSON.stringify(view),
      });

      if (!response.ok) {
        throw new Error(`Failed to create view: ${response.status} ${response.statusText}`);
      }

      const createdView: CreateViewResponse = await response.json();

      // Refetch view folders to get the updated state
      get().fetchViewFolders();

      return createdView;
    } catch (error) {
      console.error("Failed to create view:", error);
      return null;
    }
  },

  patchView: async (viewId: string, patch: PatchViewRequest) => {
    try {
      const response = await apiFetch(`/v1/views/${viewId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });

      if (!response.ok) {
        throw new Error(`Failed to patch view: ${response.status} ${response.statusText}`);
      }

      const updatedView: View = await response.json();

      set(
        produce((state: ViewsState) => {
          state.viewsMap.set(viewId, updatedView);
          // Also update in folder if it exists
          state.viewFolders.forEach((folder) => {
            const viewIndex = folder.views.findIndex((v) => v.id === viewId);
            if (viewIndex !== -1) {
              folder.views[viewIndex] = updatedView;
            }
          });
        })
      );

      return updatedView;
    } catch (error) {
      console.error("Failed to patch view:", error);
      return null;
    }
  },

  deleteView: async (viewId: string) => {
    try {
      const response = await apiFetch(`/v1/views/${viewId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        console.error(`Failed to delete view: ${response.status} ${response.statusText}`);
        return;
      }

      set(
        produce((state: ViewsState) => {
          state.viewsMap.delete(viewId);
          // Remove from folders
          state.viewFolders.forEach((folder) => {
            folder.views = folder.views.filter((v) => v.id !== viewId);
          });
        })
      );
    } catch (error) {
      console.error("Failed to delete view:", error);
    }
  },

  setPage: (page: number) => {
    const state = get();
    if (page !== state.currentPage && page > 0) {
      state.fetchViewFolders(page);
    }
  },

  setPageSize: (pageSize: number) => {
    const state = get();
    if (pageSize !== state.pageSize && pageSize > 0) {
      state.fetchViewFolders(1, pageSize);
    }
  },
}));

// Hook for fetching individual views
export const useOrFetchView = (viewId: string | undefined) => {
  const { isLoaded, isSignedIn } = useAuth();
  const fetchView = useViews((state) => state.fetchView);
  const view = useViews((state) => (viewId ? state.viewsMap.get(viewId) : undefined));

  const isLoading = useViews((state) => (viewId ? (state.isLoadingView.get(viewId) ?? false) : false));

  const error = useViews((state) => (viewId ? state.viewErrors.get(viewId) : undefined));

  const viewRef = useRef(view);
  viewRef.current = view;

  const update = useCallback(() => {
    if (viewId) {
      fetchView(viewId);
    }
  }, [fetchView, viewId]);

  useEffect(() => {
    if (!viewRef.current && viewId && isLoaded && isSignedIn) {
      fetchView(viewId);
    }
  }, [fetchView, viewId, isLoaded, isSignedIn]);

  return {
    view,
    isLoading,
    error,
    update,
  };
};

// Hook for fetching all view folders
export const useOrFetchViewFolders = () => {
  const { isLoaded, isSignedIn } = useAuth();
  const fetchViewFolders = useViews((state) => state.fetchViewFolders);
  const viewFolders = useViews((state) => state.viewFolders);
  const isLoading = useViews((state) => state.isLoadingViewFolders);
  const error = useViews((state) => state.viewFoldersError);
  const total = useViews((state) => state.total);
  const hasLoaded = useViews((state) => state.hasLoaded);
  const currentPage = useViews((state) => state.currentPage);
  const pageSize = useViews((state) => state.pageSize);
  const setPage = useViews((state) => state.setPage);
  const setPageSize = useViews((state) => state.setPageSize);

  const viewFoldersRef = useRef(viewFolders);
  viewFoldersRef.current = viewFolders;

  const update = useCallback(() => {
    fetchViewFolders();
  }, [fetchViewFolders]);

  useEffect(() => {
    if (!hasLoaded && isLoaded && isSignedIn) {
      fetchViewFolders();
    }
  }, [fetchViewFolders, hasLoaded, isLoaded, isSignedIn]);

  return {
    viewFolders,
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

// Hook for getting a specific view folder
export const useViewFolder = (folderId: string | undefined) => {
  const viewFolder = useViews((state) => (folderId ? state.viewFoldersMap.get(folderId) : undefined));

  return viewFolder;
};

// Hook for getting all views across all folders (flat list)
export const useAllViews = () => {
  const viewFolders = useViews((state) => state.viewFolders);

  const allViews = useMemo(() => {
    const views: View[] = [];
    viewFolders.forEach((folder) => {
      views.push(...folder.views);
    });
    return views;
  }, [viewFolders]);

  return allViews;
};
