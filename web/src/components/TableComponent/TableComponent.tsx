import { cx } from "class-variance-authority";
import { ReactNode, useRef, useMemo } from "react";
import { StickyTableHeaders } from "./StickyTableHeaders";
import { TableScrollbar } from "./TableScrollbar";
import { TableHeader } from "./TableHeader";
import { TableBody } from "./TableBody";
import { useTableScrolling } from "./useTableScrolling";

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
  // Sticky header overlay data - simplified version info for each column
  stickyHeaderData?: Array<{
    versionNumber: number;
    modelId: string;
    reasoningEffort?: "disabled" | "low" | "medium" | "high";
    reasoningBudget?: number;
  }>;
}

export function TableComponent({
  columnHeaders,
  rowHeaders,
  data,
  minColumnWidth = 200,
  className = "",
  minHeaderHeight = 150,
  hideScrollbar = true,
  stickyHeaderData,
}: TableProps) {
  const headerRowWidth = "240px";
  const stickyHeaderRef = useRef<HTMLDivElement>(null);
  
  const {
    containerRef,
    containerWidth,
    containerLeft,
    isHovering: _isHovering, // eslint-disable-line @typescript-eslint/no-unused-vars
    isScrolling: _isScrolling, // eslint-disable-line @typescript-eslint/no-unused-vars
    isTableBottomVisible,
    scrollRef,
    topScrollRef,
    scrollLeft,
    handleMouseEnter,
    handleMouseLeave,
    handleMainScroll,
    handleTopScroll,
    hoverTimeoutRef,
  } = useTableScrolling({
    onScrollChange: (scrollLeft) => {
      // Update CSS custom property for immediate visual feedback
      if (stickyHeaderRef.current) {
        stickyHeaderRef.current.style.setProperty('--scroll-offset', `-${scrollLeft}px`);
      }
    }
  });

  // Calculate column width based on available space and number of columns
  const columnWidth = useMemo(() => {
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
  }, [containerWidth, columnHeaders.length, minColumnWidth]);

  const headerRef = useRef<HTMLTableSectionElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);

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

      {/* Sticky header overlay */}
      {stickyHeaderData && (
        <StickyTableHeaders
          stickyHeaderData={stickyHeaderData}
          columnWidth={columnWidth}
          scrollLeft={scrollLeft}
          containerLeft={containerLeft}
          containerWidth={containerWidth}
          headerRef={headerRef}
          tableRef={tableRef}
          stickyHeaderRef={stickyHeaderRef}
        />
      )}

      {/* Scrollbar - shows at bottom of viewport when table extends beyond screen, otherwise at bottom of table */}
      {!hideScrollbar && (
        <TableScrollbar
          topScrollRef={topScrollRef}
          isTableBottomVisible={isTableBottomVisible}
          containerLeft={containerLeft}
          containerWidth={containerWidth}
          columnCount={columnHeaders.length}
          columnWidth={columnWidth}
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
        />
      )}

      <div 
        ref={scrollRef} 
        className={cx("overflow-x-auto", "scrollbar-hide")} 
        style={{ 
          WebkitOverflowScrolling: 'touch',
          overscrollBehaviorX: 'none'
        }}
        onScroll={handleMainScroll}
      >
        <table ref={tableRef} className="w-full">
          <TableHeader
            headerRef={headerRef}
            columnHeaders={columnHeaders}
            headerRowWidth={headerRowWidth}
            columnWidth={columnWidth}
            minHeaderHeight={minHeaderHeight}
          />
          <TableBody
            rowHeaders={rowHeaders}
            data={data}
            headerRowWidth={headerRowWidth}
            columnWidth={columnWidth}
          />
        </table>
      </div>
    </div>
  );
}
