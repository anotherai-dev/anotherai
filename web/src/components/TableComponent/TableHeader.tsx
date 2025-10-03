import { MutableRefObject, ReactNode } from "react";
import { FirstColumnResizer } from "./FirstColumnResizer";

interface TableHeaderProps {
  headerRef: MutableRefObject<HTMLTableSectionElement | null>;
  columnHeaders: ReactNode[];
  headerRowWidth: string;
  columnWidth: number; // For backwards compatibility
  columnWidths?: number[]; // Individual column widths
  minHeaderHeight: number;
  onFirstColumnWidthChange?: (width: number) => void;
  firstColumnWidth?: number;
}

export function TableHeader({
  headerRef,
  columnHeaders,
  headerRowWidth,
  columnWidth,
  columnWidths,
  minHeaderHeight,
  onFirstColumnWidthChange,
  firstColumnWidth,
}: TableHeaderProps) {
  return (
    <thead ref={headerRef} className="bg-gray-50">
      <tr className="border-b border-gray-200">
        {/* Empty corner cell */}
        <th
          className="text-left text-xs font-medium text-gray-500 sticky left-0 bg-gray-50 z-10 relative"
          style={{
            minWidth: headerRowWidth,
            width: headerRowWidth,
            maxWidth: headerRowWidth,
            flexShrink: 0,
          }}
        >
          {/* First column resizer */}
          {onFirstColumnWidthChange && firstColumnWidth && (
            <FirstColumnResizer width={firstColumnWidth} onWidthChange={onFirstColumnWidthChange} />
          )}
        </th>
        {/* Column headers */}
        {columnHeaders.map((header, index) => {
          const width = columnWidths?.[index] || columnWidth;
          return (
            <th
              key={index}
              className="px-4 py-3 text-left text-xs font-medium text-gray-500 border-r border-gray-200 last:border-r-0 align-top"
              style={{
                width: `${width}px`,
                minWidth: `${width}px`,
                maxWidth: `${width}px`,
                height: `${minHeaderHeight}px`,
              }}
            >
              <div className="h-full flex flex-col">{header}</div>
            </th>
          );
        })}
      </tr>
    </thead>
  );
}
