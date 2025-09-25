import { MutableRefObject, ReactNode } from "react";

interface TableHeaderProps {
  headerRef: MutableRefObject<HTMLTableSectionElement | null>;
  columnHeaders: ReactNode[];
  headerRowWidth: string;
  columnWidth: number;
  minHeaderHeight: number;
}

export function TableHeader({
  headerRef,
  columnHeaders,
  headerRowWidth,
  columnWidth,
  minHeaderHeight,
}: TableHeaderProps) {
  return (
    <thead ref={headerRef} className="bg-gray-50">
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
  );
}
