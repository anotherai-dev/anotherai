"use client";

import { BarChart3, Table } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { View } from "@/types/models";
import EditableViewTitle, { EditableViewTitleRef } from "./EditableViewTitle";
import ViewMenuButton from "./ViewMenuButton";

interface ViewCellProps {
  view: View & { folder_id?: string; view_type: "run_list" | "metric" };
}

export default function ViewCell({ view }: ViewCellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const viewTitleRef = useRef<EditableViewTitleRef>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const handleViewClick = useCallback(
    (e: React.MouseEvent) => {
      // Don't navigate if we're in editing mode or if click is on input
      if (isEditing || (e.target as HTMLElement).tagName === "INPUT") {
        return;
      }
      const viewId = view.id || "view";
      router.push(`/views/${viewId}`);
    },
    [router, view.id, isEditing]
  );

  const isActive = useCallback(() => {
    const expectedPath = `/views/${view.id}`;
    return pathname === expectedPath;
  }, [pathname, view.id]);

  const handleRename = useCallback(() => {
    viewTitleRef.current?.startEditing();
  }, []);

  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      setIsDragging(true);
      e.dataTransfer.setData(
        "application/json",
        JSON.stringify({
          type: "view",
          viewId: view.id,
          sourceFolderId: view.folder_id,
        })
      );
      e.dataTransfer.effectAllowed = "move";
    },
    [view.id, view.folder_id]
  );

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <div className="relative group">
      <div
        draggable={!isEditing}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        className={`flex items-center rounded-[2px] text-xs relative cursor-move ${
          isDragging ? "opacity-50" : ""
        } ${
          isActive()
            ? "bg-blue-100 text-blue-700"
            : `text-gray-700 hover:bg-gray-100 ${isMenuOpen ? "bg-gray-100" : ""}`
        }`}
      >
        <button
          onClick={handleViewClick}
          className="flex items-start gap-1.5 pl-7 pr-3 py-2 flex-1 min-w-0 text-left"
        >
          <div className="flex-shrink-0 mt-0.5">
            {view.view_type === "run_list" ? (
              <Table className="w-3 h-3" />
            ) : (
              <BarChart3 className="w-3 h-3" />
            )}
          </div>
          <EditableViewTitle
            ref={viewTitleRef}
            viewId={view.id}
            title={view.title}
            className="pr-8"
            onEditingChange={setIsEditing}
          />
        </button>

        <ViewMenuButton
          viewId={view.id}
          viewName={view.title}
          isActive={isActive()}
          onRename={handleRename}
          onMenuOpenChange={setIsMenuOpen}
        />
      </div>
    </div>
  );
}
