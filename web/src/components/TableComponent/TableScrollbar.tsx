import { cx } from "class-variance-authority";
import { MutableRefObject, useMemo } from "react";

interface TableScrollbarProps {
  topScrollRef: MutableRefObject<HTMLDivElement | null>;
  isTableBottomVisible: boolean;
  containerLeft: number;
  containerWidth: number;
  columnCount: number;
  columnWidth: number;
  onScroll: (e: React.UIEvent<HTMLDivElement>) => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

export function TableScrollbar({
  topScrollRef,
  isTableBottomVisible,
  containerLeft,
  containerWidth,
  columnCount,
  columnWidth,
  onScroll,
  onMouseEnter,
  onMouseLeave,
}: TableScrollbarProps) {
  const headerRowWidthPx = 240;

  const scrollContentWidth = useMemo(() => {
    return columnCount * columnWidth;
  }, [columnCount, columnWidth]);

  return (
    <div
      ref={topScrollRef}
      className={cx(
        "z-50 overflow-x-scroll overflow-y-hidden h-4 bg-white border-t border-gray-200 scrollbar-always-visible",
        // Show at viewport bottom when table bottom is not visible, otherwise stick to table bottom
        !isTableBottomVisible ? "fixed" : "absolute bottom-0"
      )}
      style={{
        ...(!isTableBottomVisible
          ? {
              bottom: 0, // At bottom of viewport
              left: containerLeft + headerRowWidthPx, // Add space for the sticky header column
              width: containerWidth - headerRowWidthPx, // Reduce width by header column width
            }
          : {
              left: headerRowWidthPx, // Add space for the sticky header column
              right: 0, // Extend to the right edge of the container
            }),
        // Force scrollbar to always be visible
        scrollbarWidth: "auto", // For Firefox
        msOverflowStyle: "scrollbar", // For IE/Edge
        WebkitOverflowScrolling: "touch",
        overscrollBehaviorX: "none", // Disable horizontal bounce scrolling in Safari
      }}
      onScroll={onScroll}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div style={{ width: `${scrollContentWidth}px`, height: "1px" }} />
    </div>
  );
}
