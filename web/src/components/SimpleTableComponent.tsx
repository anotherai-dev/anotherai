import { cx } from "class-variance-authority";
import { ReactNode } from "react";

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

  return (
    <div
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

          <tbody className="bg-transparent">
            {data.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={cx(
                  "relative",
                  rowIndex < data.length - 1 &&
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
          </tbody>
        </table>
      </div>
    </div>
  );
}
