import { cx } from "class-variance-authority";
import { ReactNode, useRef } from "react";
import { useScrollbarPositioning } from "./useScrollbarPositioning";

export interface TableProps {
  // Column headers (first row)
  columnHeaders: ReactNode[];
  // Row headers (first column)
  rowHeaders: ReactNode[];
  // Data cells - array of arrays where data[rowIndex][columnIndex] is the cell content
  data: ReactNode[][];
  // Minimum width for data columns (default: 200px)
  minColumnWidth?: number;
  // Optional className for the table container
  className?: string;
  // Minimum height for headers (default: 200px)
  minHeaderHeight?: number;
  // Hide scrollbar (default: true)
  hideScrollbar?: boolean;
}

export function TableComponent({
  columnHeaders,
  rowHeaders,
  data,
  minColumnWidth = 200,
  className = "",
  minHeaderHeight = 150,
  hideScrollbar = true,
}: TableProps) {
  const headerRowWidth = "240px";
  const {
    containerRef,
    containerWidth,
    containerLeft,
    isHovering,
    isScrolling,
    isTableBottomVisible,
    handleMouseEnter,
    handleMouseLeave,
    handleScroll,
    hoverTimeoutRef,
  } = useScrollbarPositioning();

  // Calculate column width based on available space and number of columns
  const calculateColumnWidth = () => {
    const numColumns = columnHeaders.length;
    if (numColumns === 0) return minColumnWidth;

    // Available width = container width - header row width (240px) - padding/margins
    const headerRowWidthPx = 240;
    const availableWidth = containerWidth - headerRowWidthPx - 20; // 20px for padding/margins

    if (availableWidth <= 0) return minColumnWidth;

    // Calculate equal width for all columns
    const equalWidth = availableWidth / numColumns;

    // If equal width is less than minColumnWidth, use minColumnWidth (will trigger horizontal scroll)
    return Math.max(equalWidth, minColumnWidth);
  };

  const columnWidth = calculateColumnWidth();

  const scrollRef = useRef<HTMLDivElement>(null);
  const topScrollRef = useRef<HTMLDivElement>(null);

  // Sync scroll positions between top and main scroll areas
  const handleMainScroll = (e: React.UIEvent<HTMLDivElement>) => {
    if (topScrollRef.current) {
      topScrollRef.current.scrollLeft = e.currentTarget.scrollLeft;
    }
    handleScroll(); // Show scrollbar when scrolling occurs
  };

  const handleTopScroll = (e: React.UIEvent<HTMLDivElement>) => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = e.currentTarget.scrollLeft;
    }
    handleScroll(); // Show scrollbar when scrolling occurs
  };

  return (
    <div
      ref={containerRef}
      className={cx("bg-white border border-gray-200 rounded-lg overflow-hidden relative", className)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Border overlay after sticky header column - fixed position */}
      <div
        className="absolute top-0 bottom-0 border-r border-gray-200 z-20 pointer-events-none"
        style={{ left: headerRowWidth }}
      />

      {/* Scrollbar - shows at bottom of viewport when table extends beyond screen, otherwise at bottom of table */}
      {!hideScrollbar && (
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
                  left: containerLeft + 240, // Add space for the sticky header column
                  width: containerWidth - 240, // Reduce width by header column width
                }
              : {
                  left: 240, // Add space for the sticky header column
                  right: 0, // Extend to the right edge of the container
                }),
            // Force scrollbar to always be visible
            scrollbarWidth: "auto", // For Firefox
            msOverflowStyle: "scrollbar", // For IE/Edge
          }}
          onScroll={handleTopScroll}
          onMouseEnter={() => {
            // Keep scrollbar visible when hovering over it
            if (hoverTimeoutRef.current) {
              clearTimeout(hoverTimeoutRef.current);
            }
          }}
          onMouseLeave={() => {
            // Delay hiding when leaving scrollbar
            hoverTimeoutRef.current = setTimeout(() => {
              handleMouseLeave();
            }, 100);
          }}
        >
          <div style={{ width: `${columnHeaders.length * columnWidth}px`, height: "1px" }} />
        </div>
      )}

      <div ref={scrollRef} className={cx("overflow-x-auto", "scrollbar-hide")} onScroll={handleMainScroll}>
        <table className="w-full">
          {/* Header row */}
          <thead className="bg-gray-50">
            <tr className="border-b border-gray-200">
              {/* Empty corner cell */}
              <th
                className="text-left text-xs font-medium text-gray-500 sticky left-0 bg-gray-50 z-10"
                style={{
                  minWidth: headerRowWidth,
                  width: headerRowWidth,
                  maxWidth: headerRowWidth,
                }}
              ></th>
              {/* Column headers */}
              {columnHeaders.map((header, index) => (
                <th
                  key={index}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 border-r border-gray-200 last:border-r-0 align-top"
                  style={{
                    width: `${columnWidth}px`,
                    minWidth: `${columnWidth}px`,
                    maxWidth: `${columnWidth}px`,
                    height: `${minHeaderHeight}px`,
                  }}
                >
                  <div className="h-full flex flex-col">{header}</div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Body with row headers and data */}
          <tbody className="bg-white divide-y divide-gray-200">
            {rowHeaders.map((rowHeader, rowIndex) => (
              <tr key={rowIndex}>
                {/* Row header (sticky first column) */}
                <td
                  className="text-xs font-medium text-gray-500 bg-gray-50 sticky left-0 z-10 align-top"
                  style={{
                    minWidth: headerRowWidth,
                    width: headerRowWidth,
                    maxWidth: headerRowWidth,
                    height: "300px",
                  }}
                >
                  <div className="px-4 py-4">{rowHeader}</div>
                </td>

                {/* Data cells */}
                {data[rowIndex]?.map((cellContent, columnIndex) => (
                  <td
                    key={columnIndex}
                    className="px-4 py-4 text-sm border-r border-gray-200 last:border-r-0 align-top"
                    style={{
                      width: `${columnWidth}px`,
                      minWidth: `${columnWidth}px`,
                      maxWidth: `${columnWidth}px`,
                    }}
                  >
                    <div className="h-full">{cellContent}</div>
                  </td>
                )) || null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
