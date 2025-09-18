import { cx } from "class-variance-authority";
import { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";

export interface SimpleTableProps {
  // Column headers (first row)
  columnHeaders: ReactNode[];
  // Data rows - array of arrays where data[rowIndex][columnIndex] is the cell content
  data: ReactNode[][];
  // Minimum width for cells (default: 100px)
  minCellWidth?: number;
  // Optional className for the table container
  className?: string;
  // Optional row click handler
  onRowClick?: (rowIndex: number) => void;
  // Optional row hover handlers
  onRowHover?: (rowIndex: number) => void;
  onRowLeave?: () => void;
  // Vertical alignment for cell content (default: 'top')
  cellVerticalAlign?: "top" | "middle" | "bottom";
  // Column-specific width configurations
  columnWidths?: (string | number | "auto" | undefined)[];
  // Max height for the table container
  maxHeight?: string;
  // Max height for individual rows
  maxRowHeight?: string;
  // Enable lazy loading for large datasets (default: false)
  enableLazyLoading?: boolean;
  // Number of rows to render initially and load per batch (default: 50)
  lazyLoadBatchSize?: number;
  // Height of each row in pixels for virtual scrolling calculation (default: 50)
  estimatedRowHeight?: number;
}

export function SimpleTableComponent({
  columnHeaders,
  data,
  minCellWidth = 100,
  className = "",
  onRowClick,
  onRowHover,
  onRowLeave,
  cellVerticalAlign = "top",
  columnWidths,
  maxHeight,
  maxRowHeight,
  enableLazyLoading = false,
  lazyLoadBatchSize = 50,
}: SimpleTableProps) {
  const alignmentClasses = {
    top: "align-top",
    middle: "align-middle",
    bottom: "align-bottom",
  };

  const getColumnWidth = (columnIndex: number) => {
    if (!columnWidths || columnIndex >= columnWidths.length) {
      return { minWidth: `${minCellWidth}px` };
    }

    const width = columnWidths[columnIndex];

    // For undefined width (first column), don't set any width constraint to let it expand
    if (width === undefined) {
      return {};
    }

    if (width === "auto") {
      return { width: "auto" };
    }
    if (typeof width === "number") {
      return { width: `${width}px` };
    }

    return { width: width };
  };

  // Lazy loading state and logic
  const [visibleRowCount, setVisibleRowCount] = useState(enableLazyLoading ? lazyLoadBatchSize : data.length);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const tableBodyRef = useRef<HTMLTableSectionElement>(null);

  // Memoized visible data
  const visibleData = useMemo(() => {
    return enableLazyLoading ? data.slice(0, visibleRowCount) : data;
  }, [data, visibleRowCount, enableLazyLoading]);

  // Load more rows function
  const loadMoreRows = useCallback(() => {
    if (!enableLazyLoading || isLoadingMore || visibleRowCount >= data.length) {
      return;
    }

    setIsLoadingMore(true);

    // Simulate loading delay (can be removed if not needed)
    setTimeout(() => {
      setVisibleRowCount((prev) => Math.min(prev + lazyLoadBatchSize, data.length));
      setIsLoadingMore(false);
    }, 100);
  }, [enableLazyLoading, isLoadingMore, visibleRowCount, data.length, lazyLoadBatchSize]);

  // Scroll event handler for infinite scroll
  const handleScroll = useCallback(
    (e: Event) => {
      if (!enableLazyLoading) return;

      const target = e.target as HTMLElement;
      const scrollTop = target.scrollTop;
      const scrollHeight = target.scrollHeight;
      const clientHeight = target.clientHeight;

      // Load more when near bottom (within 200px)
      if (scrollHeight - scrollTop - clientHeight < 200) {
        loadMoreRows();
      }
    },
    [enableLazyLoading, loadMoreRows]
  );

  // Set up scroll listener
  useEffect(() => {
    const container = containerRef.current?.querySelector(".overflow-auto");
    if (!container || !enableLazyLoading) return;

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, [handleScroll, enableLazyLoading]);

  // Reset visible row count when data changes
  useEffect(() => {
    if (enableLazyLoading) {
      setVisibleRowCount(Math.min(lazyLoadBatchSize, data.length));
    }
  }, [data, enableLazyLoading, lazyLoadBatchSize]);

  return (
    <div
      ref={containerRef}
      className={cx(
        "bg-gradient-to-b from-white to-gray-50 border border-gray-200 rounded-[2px] overflow-hidden relative",
        className
      )}
      style={maxHeight ? { maxHeight, display: "flex", flexDirection: "column" } : undefined}
    >
      <div className={maxHeight ? "flex-1 overflow-auto" : "h-full overflow-auto"}>
        <table className="w-full">
          <thead className="bg-white sticky top-0 after:content-[''] after:absolute after:bottom-0 after:left-2 after:right-2 after:h-px after:bg-gray-200 z-20">
            <tr>
              {columnHeaders.map((header, index) => (
                <th
                  key={index}
                  className="px-4 py-3.5 text-left text-xs font-semibold text-gray-900 align-middle"
                  style={getColumnWidth(index)}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>

          <tbody ref={tableBodyRef} className="bg-transparent">
            {visibleData.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={cx(
                  "relative",
                  rowIndex < visibleData.length - 1 &&
                    "after:content-[''] after:absolute after:bottom-0 after:left-2 after:right-2 after:h-px after:bg-gray-200",
                  (onRowClick || onRowHover) && "hover:bg-gray-50",
                  onRowClick && "cursor-pointer"
                )}
                onClick={onRowClick ? () => onRowClick(rowIndex) : undefined}
                onMouseEnter={onRowHover ? () => onRowHover(rowIndex) : undefined}
                onMouseLeave={onRowLeave ? () => onRowLeave() : undefined}
              >
                {row.map((cellContent, columnIndex) => (
                  <td
                    key={columnIndex}
                    className={`px-4 py-3.5 text-xs ${alignmentClasses[cellVerticalAlign]}`}
                    style={getColumnWidth(columnIndex)}
                  >
                    {maxRowHeight ? (
                      <div
                        className="relative"
                        style={{
                          maxHeight: maxRowHeight,
                          overflowY: "clip",
                          display: "flex",
                          flexDirection: "column",
                        }}
                      >
                        {cellContent}
                      </div>
                    ) : (
                      cellContent
                    )}
                  </td>
                ))}
              </tr>
            ))}
            {enableLazyLoading && visibleRowCount < data.length && (
              <tr>
                <td colSpan={columnHeaders.length} className="px-4 py-8 text-center text-xs text-gray-500">
                  {isLoadingMore ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                      Loading more rows...
                    </div>
                  ) : (
                    <button onClick={loadMoreRows} className="text-blue-600 hover:text-blue-800 underline">
                      Load more rows ({data.length - visibleRowCount} remaining)
                    </button>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
