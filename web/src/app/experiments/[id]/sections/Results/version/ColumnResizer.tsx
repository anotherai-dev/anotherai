import { useCallback, useEffect, useRef, useState } from "react";

interface ColumnResizerProps {
  leftVersionId: string;
  rightVersionId?: string; // undefined for the rightmost column
  leftInitialWidth: number;
  onWidthChange: (versionId: string, width: number) => void;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
  className?: string;
}

export function ColumnResizer({
  leftVersionId,
  rightVersionId, // eslint-disable-line @typescript-eslint/no-unused-vars
  leftInitialWidth,
  onWidthChange,
  onResizeStart,
  onResizeEnd,
  className = "",
}: ColumnResizerProps) {
  const [isResizing, setIsResizing] = useState(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(leftInitialWidth);
  const currentWidthRef = useRef(leftInitialWidth);

  // Keep current width ref in sync with the prop
  useEffect(() => {
    currentWidthRef.current = leftInitialWidth;
  }, [leftInitialWidth]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      setIsResizing(true);
      startXRef.current = e.clientX;
      // Use the current width at the time of drag start, not the prop value
      startWidthRef.current = currentWidthRef.current;

      onResizeStart?.();

      const handleMouseMove = (e: MouseEvent) => {
        const deltaX = e.clientX - startXRef.current;
        const newWidth = Math.max(200, startWidthRef.current + deltaX); // Minimum 200px
        currentWidthRef.current = newWidth; // Keep track of current width
        onWidthChange(leftVersionId, newWidth);
      };

      const handleMouseUp = () => {
        setIsResizing(false);
        onResizeEnd?.();
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    },
    [leftVersionId, onWidthChange, onResizeStart, onResizeEnd]
  );

  return (
    <div
      className={`absolute top-0 bottom-0 w-1 cursor-col-resize group z-20 ${className}`}
      style={{ right: "-16px", transform: "translateX(50%)" }}
      onMouseDown={handleMouseDown}
    >
      {/* Wider hover area for easier grabbing */}
      <div className="absolute top-0 bottom-0 -left-3 -right-3" />

      {/* Visual indicator */}
      <div
        className={`absolute top-0 bottom-0 w-0.5 bg-transparent group-hover:bg-blue-500 transition-colors ${
          isResizing ? "bg-blue-500" : ""
        }`}
        style={{ left: "50%", transform: "translateX(-50%)" }}
      />
    </div>
  );
}
