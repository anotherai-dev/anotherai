import { ReactNode } from "react";

interface TableBodyProps {
  rowHeaders: ReactNode[];
  data: ReactNode[][];
  headerRowWidth: string;
  columnWidth: number; // For backwards compatibility
  columnWidths?: number[]; // Individual column widths
}

export function TableBody({ rowHeaders, data, headerRowWidth, columnWidth, columnWidths }: TableBodyProps) {
  return (
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
          {data[rowIndex]?.map((cellContent, columnIndex) => {
            const width = columnWidths?.[columnIndex] || columnWidth;
            return (
              <td
                key={columnIndex}
                className="px-4 py-4 text-sm border-r border-gray-200 last:border-r-0 align-top"
                style={{
                  width: `${width}px`,
                  minWidth: `${width}px`,
                  maxWidth: `${width}px`,
                }}
              >
                <div className="h-full">{cellContent}</div>
              </td>
            );
          }) || null}
        </tr>
      ))}
    </tbody>
  );
}
