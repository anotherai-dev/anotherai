import { GripVertical } from "lucide-react";
import { ReactNode, useCallback, useState } from "react";
import { ColumnResizer } from "./ColumnResizer";

interface DraggableColumnWrapperProps {
  children: ReactNode;
  onReorderColumns?: (fromIndex: number, toIndex: number) => void;
  dragIndex?: number;
  versionId: string;
  className?: string;
  // Column resizing props
  columnWidth?: number;
  onColumnWidthChange?: (versionId: string, width: number) => void;
  nextVersionId?: string;
  isLastColumn?: boolean;
}

export function DraggableColumnWrapper({
  children,
  onReorderColumns,
  dragIndex,
  versionId,
  className = "",
  columnWidth,
  onColumnWidthChange,
  nextVersionId,
  isLastColumn = false, // eslint-disable-line @typescript-eslint/no-unused-vars
}: DraggableColumnWrapperProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [dragOver, setDragOver] = useState<"left" | "right" | null>(null);

  // Drag and drop handlers
  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      if (!onReorderColumns || dragIndex === undefined) return;

      setIsDragging(true);
      e.dataTransfer.setData(
        "application/json",
        JSON.stringify({
          type: "column",
          dragIndex,
          versionId,
        })
      );
      e.dataTransfer.effectAllowed = "move";
    },
    [onReorderColumns, dragIndex, versionId]
  );

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
    setDragOver(null);
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      if (!onReorderColumns) return;

      e.preventDefault();
      e.dataTransfer.dropEffect = "move";

      // Determine if we're dragging over left or right half
      const rect = e.currentTarget.getBoundingClientRect();
      const midpoint = rect.left + rect.width / 2;
      const dropSide = e.clientX < midpoint ? "left" : "right";
      setDragOver(dropSide);
    },
    [onReorderColumns]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    // Only clear drag over if we're leaving the column entirely
    const rect = e.currentTarget.getBoundingClientRect();
    const { clientX, clientY } = e;

    if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) {
      setDragOver(null);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      if (!onReorderColumns || dragIndex === undefined) return;

      e.preventDefault();

      try {
        const data = JSON.parse(e.dataTransfer.getData("application/json"));

        if (data.type === "column" && typeof data.dragIndex === "number") {
          const fromIndex = data.dragIndex;
          let toIndex = dragIndex;

          // Adjust target index based on which half we dropped on
          if (dragOver === "right") {
            toIndex += 1;
          }

          // Don't reorder if dropping in same position
          if (fromIndex !== toIndex && fromIndex !== toIndex - 1) {
            onReorderColumns(fromIndex, toIndex > fromIndex ? toIndex - 1 : toIndex);
          }
        }
      } catch (error) {
        console.error("Failed to parse drop data:", error);
      }

      setDragOver(null);
    },
    [onReorderColumns, dragIndex, dragOver]
  );

  return (
    <div
      className={`relative ${isDragging ? "opacity-50" : ""} ${className}`}
      draggable={onReorderColumns !== undefined}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drop indicator lines - positioned at table column borders */}
      {dragOver === "left" && (
        <div className="absolute top-0 bottom-0 w-[2px] bg-blue-500 z-100" style={{ left: "-17px" }} />
      )}
      {dragOver === "right" && (
        <div className="absolute top-0 bottom-0 w-[2px] bg-blue-500 z-100" style={{ right: "-17px" }} />
      )}

      {/* Drag handle - shown when drag is available */}
      {onReorderColumns && (
        <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 z-3">
          <div
            className="bg-gray-100 hover:bg-gray-200 rounded px-1 py-0.5 cursor-grab active:cursor-grabbing opacity-60 hover:opacity-100 transition-opacity"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <GripVertical className="w-3 h-3 text-gray-500" />
          </div>
        </div>
      )}

      {children}

      {/* Column resizer - show for all columns */}
      {onColumnWidthChange && columnWidth && (
        <ColumnResizer
          leftVersionId={versionId}
          rightVersionId={nextVersionId}
          leftInitialWidth={columnWidth}
          onWidthChange={onColumnWidthChange}
        />
      )}
    </div>
  );
}
