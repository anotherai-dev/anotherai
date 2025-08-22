"use client";

import { Plus } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { useOrFetchViewFolders, useViews } from "@/store/views";
import { View } from "@/types/models";
import { EditableFolderNameRef } from "./EditableFolderName";
import FolderCell from "./FolderCell";

export default function ViewsSection() {
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [openFolderMenus, setOpenFolderMenus] = useState<Set<string>>(new Set());
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const folderRefs = useRef<Map<string, EditableFolderNameRef>>(new Map());

  // Use views store with view folders
  const { viewFolders, error, update, isLoading } = useOrFetchViewFolders();
  const { createViewFolder, patchView } = useViews();

  // Track if we're currently updating to prevent race conditions
  const isUpdatingRef = useRef(false);
  const lastUpdateTimeRef = useRef<number>(0);
  const pendingUpdateRef = useRef<NodeJS.Timeout | null>(null);

  const toggleFolderCollapse = useCallback((folderId: string) => {
    setCollapsedFolders((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  }, []);

  const handleCreateFolder = useCallback(async () => {
    if (isCreatingFolder) return;

    setIsCreatingFolder(true);
    try {
      await createViewFolder({ name: "New Folder" });
    } catch (error) {
      console.error("Failed to create folder:", error);
    } finally {
      setIsCreatingFolder(false);
    }
  }, [createViewFolder, isCreatingFolder]);

  const handleFolderMenuOpenChange = useCallback((folderId: string, isOpen: boolean) => {
    setOpenFolderMenus((prev) => {
      const newSet = new Set(prev);
      if (isOpen) {
        newSet.add(folderId);
      } else {
        newSet.delete(folderId);
      }
      return newSet;
    });
  }, []);

  // Debounced update function to prevent race conditions
  const debouncedUpdate = useCallback(async () => {
    // Clear any pending update
    if (pendingUpdateRef.current) {
      clearTimeout(pendingUpdateRef.current);
      pendingUpdateRef.current = null;
    }

    // Check if we're already updating or if an update was too recent
    const now = Date.now();
    const timeSinceLastUpdate = now - lastUpdateTimeRef.current;
    const minTimeBetweenUpdates = 1000; // 1 second minimum between updates

    if (isUpdatingRef.current || timeSinceLastUpdate < minTimeBetweenUpdates) {
      // Schedule an update for later if not already scheduled
      if (!pendingUpdateRef.current && timeSinceLastUpdate < minTimeBetweenUpdates) {
        const delay = minTimeBetweenUpdates - timeSinceLastUpdate;
        pendingUpdateRef.current = setTimeout(() => {
          pendingUpdateRef.current = null;
          debouncedUpdate();
        }, delay);
      }
      return;
    }

    // Proceed with the update
    isUpdatingRef.current = true;
    lastUpdateTimeRef.current = now;

    try {
      await update();
    } catch (error) {
      console.error("Failed to update views:", error);
    } finally {
      isUpdatingRef.current = false;
    }
  }, [update]);

  const handleDragOver = useCallback((e: React.DragEvent, folderId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverFolder(folderId);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    // Only clear drag over if we're leaving the folder container entirely
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setDragOverFolder(null);
    }
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent, targetFolderId: string) => {
      e.preventDefault();
      setDragOverFolder(null);

      try {
        const rawData = e.dataTransfer.getData("application/json");
        if (!rawData) {
          console.warn("No drag data found");
          return;
        }

        let dragData;
        try {
          dragData = JSON.parse(rawData);
        } catch (parseError) {
          console.error("Failed to parse drag data:", parseError);
          return;
        }

        if (!dragData || typeof dragData !== "object") {
          console.error("Invalid drag data format:", dragData);
          return;
        }

        if (dragData.type === "view") {
          const { viewId, sourceFolderId } = dragData;

          if (!viewId || sourceFolderId === undefined || sourceFolderId === null) {
            console.error("Missing required drag data fields:", {
              viewId,
              sourceFolderId,
            });
            return;
          }

          // Don't do anything if dropped on the same folder
          if (sourceFolderId === targetFolderId) {
            return;
          }

          // Update the view's folder
          await patchView(viewId, { folder_id: targetFolderId });

          // Refetch to get updated state using debounced update
          await debouncedUpdate();
        }
      } catch (error) {
        console.error("Failed to move view:", error);
      }
    },
    [patchView, debouncedUpdate]
  );

  // Listen for drag operations globally to show drop zones
  useEffect(() => {
    const handleDragEnter = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes("application/json")) {
        setIsDragActive(true);
      }
    };

    const handleDragEnd = () => {
      setIsDragActive(false);
      setDragOverFolder(null);
    };

    document.addEventListener("dragenter", handleDragEnter);
    document.addEventListener("dragend", handleDragEnd);

    return () => {
      document.removeEventListener("dragenter", handleDragEnter);
      document.removeEventListener("dragend", handleDragEnd);
    };
  }, []);

  // Auto-refresh functionality with race condition protection
  useEffect(() => {
    const interval = setInterval(async () => {
      // Only update if page is visible and not currently loading
      if (!document.hidden && !isLoading) {
        debouncedUpdate();
      }
    }, 5000);

    return () => {
      clearInterval(interval);
      // Clean up any pending updates
      if (pendingUpdateRef.current) {
        clearTimeout(pendingUpdateRef.current);
        pendingUpdateRef.current = null;
      }
    };
  }, [debouncedUpdate, isLoading]);

  // Cleanup pending updates on unmount
  useEffect(() => {
    return () => {
      if (pendingUpdateRef.current) {
        clearTimeout(pendingUpdateRef.current);
      }
    };
  }, []);

  // Process view folders data - show all folders, even if empty
  const viewsByFolder = useMemo(() => {
    return viewFolders.reduce(
      (acc, folder) => {
        acc[folder.id] = {
          name: folder.name,
          views:
            folder.views?.map((view) => ({
              ...view,
              folder_id: folder.id,
              view_type: view.graph?.type === "table" ? ("run_list" as const) : ("metric" as const),
            })) || [],
        };
        return acc;
      },
      {} as Record<
        string,
        {
          name: string;
          views: Array<View & { folder_id: string; view_type: "run_list" | "metric" }>;
        }
      >
    );
  }, [viewFolders]);

  return (
    <div className="flex flex-col flex-1 py-2 min-h-0">
      <div className="flex flex-col flex-1 px-2 min-h-0">
        {/* Views Header */}
        <div className="flex items-center justify-between pl-3 pr-[9px] py-2 mb-1 text-[11px] font-medium text-gray-500 uppercase tracking-wider">
          <span>Views</span>
          <HoverPopover content="Create new folder" position="top" popoverClassName="bg-gray-800 rounded-[2px]">
            <button
              onClick={handleCreateFolder}
              disabled={isCreatingFolder}
              className="p-1 rounded hover:bg-gray-200 hover:text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <Plus className="w-3 h-3" />
            </button>
          </HoverPopover>
        </div>

        {/* Main content area with flex-1 to take remaining space */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {error ? (
            <div className="px-3">
              <p className="text-xs text-red-600">{error.message}</p>
              <button onClick={debouncedUpdate} className="mt-2 text-xs text-blue-600 hover:text-blue-800">
                Try again
              </button>
            </div>
          ) : Object.keys(viewsByFolder).length === 0 ? (
            <div className="px-3 text-center">
              <p className="text-xs text-gray-500">No saved views yet</p>
            </div>
          ) : (
            <>
              {/* Render all view folders */}
              {Object.entries(viewsByFolder).map(([folderId, folderData]) => {
                // Auto-collapse folders with no views by default
                const hasViews = folderData.views.length > 0;
                const isCollapsed = hasViews ? collapsedFolders.has(folderId) : !collapsedFolders.has(folderId);
                const isMenuOpen = openFolderMenus.has(folderId);
                const isDragOver = dragOverFolder === folderId;

                return (
                  <FolderCell
                    key={folderId}
                    folderId={folderId}
                    folderName={folderData.name}
                    views={folderData.views}
                    isCollapsed={isCollapsed}
                    isMenuOpen={isMenuOpen}
                    isDragOver={isDragOver}
                    isDragActive={isDragActive}
                    onToggleCollapse={() => toggleFolderCollapse(folderId)}
                    onMenuOpenChange={(isOpen) => handleFolderMenuOpenChange(folderId, isOpen)}
                    onDragOver={(e) => handleDragOver(e, folderId)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, folderId)}
                    onRefChange={(ref) => {
                      if (ref) {
                        folderRefs.current.set(folderId, ref);
                      } else {
                        folderRefs.current.delete(folderId);
                      }
                    }}
                  />
                );
              })}
            </>
          )}
        </div>
      </div>

      {/* Auto-refresh indicator */}
      <div className="px-3 pt-3 pb-1 border-t border-gray-200 mt-3">
        <p className="text-xs text-gray-400 text-center">Views update automatically</p>
      </div>
    </div>
  );
}
