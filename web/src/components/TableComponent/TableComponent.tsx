import { cx } from "class-variance-authority";
import { ReactNode, useMemo, useRef } from "react";
import { StickyTableHeaders } from "./StickyTableHeaders";
import { TableBody } from "./TableBody";
import { TableHeader } from "./TableHeader";
import { TableScrollbar } from "./TableScrollbar";
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
  // Custom column widths array (if not provided, equal widths are used)
  columnWidths?: number[];
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
  columnWidths,
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
    hasHorizontalScroll,
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
        stickyHeaderRef.current.style.setProperty("--scroll-offset", `-${scrollLeft}px`);
      }
    },
  });

  // Calculate column widths - use custom widths if provided, otherwise equal widths
  const calculatedColumnWidths = useMemo(() => {
    const numColumns = columnHeaders.length;
    if (numColumns === 0) return [];

    // If custom column widths are provided, use them with a minimum of 200px
    if (columnWidths && columnWidths.length === numColumns) {
      return columnWidths.map((width) => Math.max(width, 200)); // Always 200px minimum for custom widths
    }

    // Available width = container width - header row width (240px) - padding/margins
    const headerRowWidthPx = 240;
    const availableWidth = containerWidth - headerRowWidthPx - 20; // 20px for padding/margins

    if (availableWidth <= 0) {
      return new Array(numColumns).fill(minColumnWidth);
    }

    // Calculate equal width for all columns
    const equalWidth = availableWidth / numColumns;
    const finalWidth = Math.max(equalWidth, minColumnWidth);

    return new Array(numColumns).fill(finalWidth);
  }, [containerWidth, columnHeaders.length, minColumnWidth, columnWidths]);

  // For backwards compatibility, provide a single columnWidth value (first column's width or default)
  const columnWidth = calculatedColumnWidths.length > 0 ? calculatedColumnWidths[0] : minColumnWidth;

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
      {!hideScrollbar && hasHorizontalScroll && (
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
          WebkitOverflowScrolling: "touch",
          overscrollBehaviorX: "none",
        }}
        onScroll={handleMainScroll}
      >
        <table ref={tableRef} className="w-full">
          <TableHeader
            headerRef={headerRef}
            columnHeaders={columnHeaders}
            headerRowWidth={headerRowWidth}
            columnWidth={columnWidth}
            columnWidths={calculatedColumnWidths}
            minHeaderHeight={minHeaderHeight}
          />
          <TableBody
            rowHeaders={rowHeaders}
            data={data}
            headerRowWidth={headerRowWidth}
            columnWidth={columnWidth}
            columnWidths={calculatedColumnWidths}
          />
        </table>
      </div>
    </div>
  );
}
