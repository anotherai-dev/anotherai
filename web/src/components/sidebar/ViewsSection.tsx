"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useOrFetchViewFolders } from "@/store/views";
import { View } from "@/types/models";
import ViewCell from "./ViewCell";

export default function ViewsSection() {
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(
    new Set()
  );

  // Use views store with view folders
  const { viewFolders, error, update, isLoading } = useOrFetchViewFolders();

  // Track if we're currently updating to prevent race conditions
  const isUpdatingRef = useRef(false);

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

  // Auto-refresh functionality - less frequent to reduce blinking
  useEffect(() => {
    const interval = setInterval(async () => {
      // Only update if page is visible and not already updating
      if (!document.hidden && !isUpdatingRef.current && !isLoading) {
        isUpdatingRef.current = true;
        try {
          await update();
        } finally {
          isUpdatingRef.current = false;
        }
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [update, isLoading]); // Include update and isLoading in dependencies

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
              view_type:
                view.graph?.type === "table"
                  ? ("run_list" as const)
                  : ("metric" as const),
            })) || [],
        };
        return acc;
      },
      {} as Record<
        string,
        {
          name: string;
          views: Array<
            View & { folder_id: string; view_type: "run_list" | "metric" }
          >;
        }
      >
    );
  }, [viewFolders]);

  return (
    <div className="flex flex-col flex-1 p-2 min-h-0">
      {/* Views Header */}
      <div className="flex items-center px-3 py-2 mb-1 text-[11px] font-medium text-gray-400 uppercase tracking-wider">
        Views
      </div>

      {/* Main content area with flex-1 to take remaining space */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {error ? (
          <div className="px-3">
            <p className="text-xs text-red-600">{error.message}</p>
            <button
              onClick={update}
              className="mt-2 text-xs text-blue-600 hover:text-blue-800"
            >
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
              const isCollapsed = collapsedFolders.has(folderId);
              return (
                <div key={folderId} className="mb-3">
                  <div className="flex items-center px-3 py-1">
                    <button
                      onClick={() => toggleFolderCollapse(folderId)}
                      className="flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-gray-600 transition-colors flex-1"
                    >
                      <span>{folderData.name || "Unnamed"}</span>
                      {isCollapsed ? (
                        <ChevronRight className="w-3 h-3" />
                      ) : (
                        <ChevronDown className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                  {!isCollapsed && (
                    <div className="space-y-1">
                      {folderData.views.length > 0 ? (
                        folderData.views.map((view) => (
                          <div key={view.id} className="group">
                            <ViewCell view={view} />
                          </div>
                        ))
                      ) : (
                        <div className="px-3 py-2 text-xs text-gray-400 italic">
                          No views in this folder
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Auto-refresh indicator */}
      <div className="px-3 pt-3 pb-2 border-t border-gray-200 mt-3">
        <p className="text-xs text-gray-400 text-center">
          Views update automatically
        </p>
      </div>
    </div>
  );
}
