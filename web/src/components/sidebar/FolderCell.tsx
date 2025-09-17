"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import React, { useCallback, useRef } from "react";
import { View } from "@/types/models";
import EditableFolderName, { EditableFolderNameRef } from "./EditableFolderName";
import FolderMenuButton from "./FolderMenuButton";
import ViewCell from "./ViewCell";

interface FolderCellProps {
  folderId: string;
  folderName: string;
  views: Array<View & { folder_id: string; view_type: "run_list" | "metric" }>;
  isCollapsed: boolean;
  isMenuOpen: boolean;
  isDragOver: boolean;
  isDragActive: boolean;
  onToggleCollapse: () => void;
  onMenuOpenChange: (isOpen: boolean) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onRefChange: (ref: EditableFolderNameRef | null) => void;
}

function FolderCell({
  folderId,
  folderName,
  views,
  isCollapsed,
  isMenuOpen,
  isDragOver,
  isDragActive,
  onToggleCollapse,
  onMenuOpenChange,
  onDragOver,
  onDragLeave,
  onDrop,
  onRefChange,
}: FolderCellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const folderRef = useRef<EditableFolderNameRef>(null);

  const handleRename = useCallback(() => {
    folderRef.current?.startEditing();
  }, []);

  const handleFolderClick = useCallback(
    (e: React.MouseEvent) => {
      // Don't navigate if we're editing the name or if click is on input
      if (folderRef.current?.isEditing() || (e.target as HTMLElement).tagName === "INPUT") {
        return;
      }
      // Navigate to folder page if folder has an ID (not the empty folder)
      if (folderId && folderId !== "") {
        router.push(`/folders/${folderId}`);
      }
    },
    [router, folderId]
  );

  const isActive = useCallback(() => {
    if (!folderId || folderId === "") return false;
    const expectedPath = `/folders/${folderId}`;
    return pathname === expectedPath;
  }, [pathname, folderId]);

  return (
    <div className="mb-0.5">
      <div
        className={`flex items-center pl-3 pr-2 group/folder transition-colors rounded-[2px] ${
          isDragOver
            ? "bg-blue-200 border border-blue-600 border-dashed"
            : isDragActive
              ? "border border-transparent border-dashed"
              : isActive()
                ? "bg-blue-100"
                : ""
        } ${
          isMenuOpen ? "hover:bg-gray-100 bg-gray-100" : !isActive() ? "hover:bg-gray-100" : "hover:bg-blue-200"
        } ${folderId === "" ? "py-2" : "py-1"}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <div className="flex items-center flex-1 gap-1">
          <button
            onClick={onToggleCollapse}
            className={`flex items-center justify-center w-4 h-4 transition-colors ${
              isActive() ? "text-blue-700" : isDragOver ? "text-gray-800" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {isCollapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          <button
            onClick={handleFolderClick}
            className={`flex items-center text-xs font-medium transition-colors flex-1 cursor-pointer min-w-0 ${
              isActive() ? "text-blue-700" : isDragOver ? "text-gray-800" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <EditableFolderName
              ref={(ref) => {
                folderRef.current = ref;
                onRefChange(ref);
              }}
              folderId={folderId}
              name={folderName}
            />
          </button>
        </div>
        <FolderMenuButton
          folderId={folderId}
          folderName={folderName}
          onRename={handleRename}
          onMenuOpenChange={onMenuOpenChange}
        />
      </div>
      {!isCollapsed && (
        <div className="space-y-1" onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
          {views.length > 0 ? (
            views.map((view) => (
              <div key={view.id} className="group">
                <ViewCell view={view} />
              </div>
            ))
          ) : (
            <div className="pl-7 pr-3 py-0.5 text-xs text-gray-400 italic">No views in this folder</div>
          )}
        </div>
      )}
    </div>
  );
}

// Helper function to compare view arrays for memoization
function areViewArraysEqual(
  prevViews: Array<View & { folder_id: string; view_type: "run_list" | "metric" }>,
  nextViews: Array<View & { folder_id: string; view_type: "run_list" | "metric" }>
): boolean {
  if (prevViews.length !== nextViews.length) {
    return false;
  }

  for (let i = 0; i < prevViews.length; i++) {
    const prev = prevViews[i];
    const next = nextViews[i];

    if (
      prev.id !== next.id ||
      prev.title !== next.title ||
      prev.folder_id !== next.folder_id ||
      prev.view_type !== next.view_type ||
      prev.graph?.type !== next.graph?.type
    ) {
      return false;
    }
  }

  return true;
}

// Memoize FolderCell to prevent unnecessary re-renders
export default React.memo(FolderCell, (prevProps, nextProps) => {
  // Compare all props that affect rendering
  return (
    prevProps.folderId === nextProps.folderId &&
    prevProps.folderName === nextProps.folderName &&
    prevProps.isCollapsed === nextProps.isCollapsed &&
    prevProps.isMenuOpen === nextProps.isMenuOpen &&
    prevProps.isDragOver === nextProps.isDragOver &&
    prevProps.isDragActive === nextProps.isDragActive &&
    areViewArraysEqual(prevProps.views, nextProps.views)
    // Note: Function props (callbacks) are not compared as they're typically stable
    // due to useCallback in the parent component
  );
});

export { type EditableFolderNameRef };
