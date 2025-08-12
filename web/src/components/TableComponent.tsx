import { cx } from "class-variance-authority";
import { ReactNode } from "react";

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
}

export function TableComponent({
  columnHeaders,
  rowHeaders,
  data,
  minColumnWidth = 200,
  className = "",
  minHeaderHeight = 150,
}: TableProps) {
  const headerRowWidth = "240px";

  return (
    <div
      className={cx(
        "bg-white border border-gray-200 rounded-lg overflow-hidden relative",
        className
      )}
    >
      {/* Border overlay after sticky header column - fixed position */}
      <div
        className="absolute top-0 bottom-0 border-r border-gray-200 z-20 pointer-events-none"
        style={{ left: headerRowWidth }}
      />
      <div className="overflow-x-auto scrollbar-hide">
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
                    minWidth: `${minColumnWidth}px`,
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
                      minWidth: `${minColumnWidth}px`,
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
