import { useCallback, useMemo } from "react";
import { useLocalStorage } from "usehooks-ts";

/**
 * A hook for managing column widths in experiments with localStorage persistence
 */
export function useColumnWidths(experimentId: string, versionIds: string[], defaultWidth: number = 400) {
  const [columnWidths, setColumnWidths] = useLocalStorage<Record<string, number>>(`column-widths-${experimentId}`, {});

  // Function to set width for a specific column
  const setColumnWidth = useCallback(
    (versionId: string, width: number) => {
      setColumnWidths((prev) => ({
        ...prev,
        [versionId]: Math.max(200, width), // Minimum width of 200px
      }));
    },
    [setColumnWidths]
  );

  // Function to get width for a specific column
  const getColumnWidth = useCallback(
    (versionId: string) => {
      return columnWidths[versionId] || defaultWidth;
    },
    [columnWidths, defaultWidth]
  );

  // Function to reset all column widths
  const resetColumnWidths = useCallback(() => {
    setColumnWidths({});
  }, [setColumnWidths]);

  // Function to reset width for a specific column
  const resetColumnWidth = useCallback(
    (versionId: string) => {
      setColumnWidths((prev) => {
        const newWidths = { ...prev };
        delete newWidths[versionId];
        return newWidths;
      });
    },
    [setColumnWidths]
  );

  // Get all current widths as an array in the order of versionIds
  const widthsArray = useMemo(() => {
    return versionIds.map((versionId) => getColumnWidth(versionId));
  }, [versionIds, getColumnWidth]);

  // Check if any columns have custom widths
  const hasCustomWidths = useMemo(() => {
    return Object.keys(columnWidths).length > 0;
  }, [columnWidths]);

  return {
    columnWidths,
    setColumnWidth,
    getColumnWidth,
    resetColumnWidths,
    resetColumnWidth,
    widthsArray,
    hasCustomWidths,
  };
}
