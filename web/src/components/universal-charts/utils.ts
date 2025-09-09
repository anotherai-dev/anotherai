// Chart utilities
export interface SeriesConfig {
  key: string;
  color: string;
  name?: string;
}

// Default color palette for charts - consistent across all chart types
export const DEFAULT_CHART_COLORS = [
  "#3b82f6",
  "#ef4444",
  "#10b981",
  "#f59e0b",
  "#8b5cf6",
  "#06b6d4",
  "#f97316",
  "#84cc16",
  "#ec4899",
  "#6366f1",
  "#14b8a6",
  "#f472b6",
  "#a855f7",
  "#eab308",
  "#22c55e",
  "#fb7185",
  "#38bdf8",
  "#fbbf24",
  "#a78bfa",
  "#34d399",
  "#f87171",
  "#60a5fa",
  "#fcd34d",
  "#c084fc",
  "#4ade80",
  "#fb923c",
  "#2dd4bf",
  "#f9a8d4",
  "#818cf8",
  "#facc15",
  "#ff6b6b",
  "#4ecdc4",
  "#45b7d1",
  "#f9ca24",
  "#f0932b",
  "#eb4d4b",
  "#6c5ce7",
  "#a29bfe",
  "#fd79a8",
  "#e17055",
];

// Transform data to ensure it has an 'x' field for automatic chart detection
export function ensureXFieldForChart(data: Record<string, unknown>[]): Record<string, unknown>[] {
  if (data.length === 0) {
    return data;
  }

  const firstRow = data[0];
  const keys = Object.keys(firstRow);

  // If data already has 'x' field, no transformation needed
  if (firstRow.x !== undefined) {
    return data;
  }

  // Try to detect which field should be the x-axis
  const potentialXAxisFields = ["date", "time", "timestamp", "category", "name", "label"];
  const xAxisField = keys.find((key) => potentialXAxisFields.includes(key.toLowerCase()));

  // If no common x-axis field found, look for fields that contain date-like or categorical data
  let detectedXAxisField = xAxisField;
  if (!detectedXAxisField) {
    detectedXAxisField = keys.find((key) => {
      const value = firstRow[key];
      if (typeof value === "string") {
        // Check if it looks like a date or is a non-numeric string (category)
        return /^\d{4}-\d{2}-\d{2}/.test(value) || /^\d{2}\/\d{2}\/\d{4}/.test(value) || isNaN(Number(value));
      }
      return false;
    });
  }

  // If we found a field to use as x-axis, transform the data
  if (detectedXAxisField) {
    return data.map((row) => ({
      ...row,
      x: row[detectedXAxisField],
    }));
  }

  // No suitable x-axis field found, return data as-is
  return data;
}

// Auto-detect series from chart data - common logic for all chart types
export function autoDetectSeries(data: Record<string, unknown>[], providedSeries?: SeriesConfig[]): SeriesConfig[] {
  if (providedSeries && providedSeries.length > 0) {
    return providedSeries;
  }

  if (data.length === 0) {
    return [];
  }

  const firstRow = data[0];
  const keys = Object.keys(firstRow);

  // If data has 'y' field, it's likely single series data that hasn't been transformed
  if (firstRow.y !== undefined) {
    return [];
  }

  // Try to detect which field is the x-axis (categorical/date field)
  // Common x-axis field names
  const potentialXAxisFields = ["x", "date", "time", "timestamp", "category", "name", "label"];
  const xAxisField = keys.find((key) => potentialXAxisFields.includes(key.toLowerCase()));

  // If no common x-axis field found, look for fields that contain date-like or categorical data
  let detectedXAxisField = xAxisField;
  if (!detectedXAxisField) {
    // Look for fields that might be dates or categories (string values)
    detectedXAxisField = keys.find((key) => {
      const value = firstRow[key];
      if (typeof value === "string") {
        // Check if it looks like a date
        return /^\d{4}-\d{2}-\d{2}/.test(value) || /^\d{2}\/\d{2}\/\d{4}/.test(value) || isNaN(Number(value)); // Non-numeric string (category)
      }
      return false;
    });
  }

  // Auto-detect series from keys, excluding the detected x-axis field and standard x/y fields
  const seriesKeys = keys.filter((key) => {
    if (key === detectedXAxisField) return false;
    if (key === "x") return false; // Always exclude x field
    if (key === "y") return false; // Always exclude explicit y field

    // Include all other fields - let the chart handle the values
    return true;
  });

  if (seriesKeys.length === 0) {
    return [];
  }

  return seriesKeys.map((key, index) => ({
    key,
    color: DEFAULT_CHART_COLORS[index % DEFAULT_CHART_COLORS.length],
    name: key,
  }));
}

// Helper function to determine X-axis key from graph configuration
function getXAxisKey(graph: { x?: { field: string } } | undefined, availableKeys: string[]): string {
  if (graph && "x" in graph && graph.x?.field) {
    return graph.x.field;
  }

  // Try to detect which field should be the x-axis using the same logic as ensureXFieldForChart
  const potentialXAxisFields = ["x", "date", "time", "timestamp", "category", "name", "label"];
  const detectedXField = availableKeys.find((key) => potentialXAxisFields.includes(key.toLowerCase()));

  if (detectedXField) {
    return detectedXField;
  }

  return availableKeys[0];
}

// Helper function to determine Y-axis key from graph configuration
function getYAxisKey(
  graph: { y?: Array<{ field: string }> } | undefined,
  availableKeys: string[],
  xAxisKey: string
): string {
  if (graph && "y" in graph && graph.y?.[0]?.field) {
    return graph.y[0].field;
  }

  // Find first key that's different from xAxisKey, or fallback to first key
  const alternativeKey = availableKeys.find((key) => key !== xAxisKey);
  return alternativeKey || availableKeys[0];
}

/**
 * Comprehensive data transformation function that handles all chart data preparation.
 * This consolidates the logic from CompletionsGraph's transformDataForChart function
 * and eliminates the "double recognition of series" issue.
 */
export interface CompletionsGraphTransformOptions {
  data: Record<string, unknown>[];
  graph: {
    type: "bar" | "line" | "pie" | "scatter" | "table";
    x?: { field: string };
    y?: Array<{ field: string; label?: string; color_hex?: string }>;
    stacked?: boolean;
  };
}

export function transformDataForCompletionsGraph({
  data,
  graph,
}: CompletionsGraphTransformOptions): Record<string, unknown>[] {
  if (!data || data.length === 0) return [];

  // Table graphs don't need data transformation for charts
  if (graph.type === "table") return [];

  // Safely get first item to extract keys
  const firstItem = data[0];
  if (!firstItem || typeof firstItem !== "object") return [];

  const availableKeys = Object.keys(firstItem);
  if (availableKeys.length === 0) return [];

  const xAxisKey = getXAxisKey(graph, availableKeys);
  const yAxisKey = getYAxisKey(graph, availableKeys, xAxisKey);

  // Check if we have multiple Y axes defined (for line charts)
  if (graph.type === "line" && "y" in graph && graph.y && graph.y.length > 1) {
    // Multi-Y axis line chart - transform data to include multiple Y series
    return data.map((item) => {
      if (!item || typeof item !== "object") {
        return { x: "" };
      }

      const transformedItem: Record<string, unknown> = {
        x: String(item[xAxisKey] || ""),
      };

      // Add each Y axis as a separate series
      if ("y" in graph && graph.y) {
        graph.y.forEach((yAxis) => {
          transformedItem[yAxis.field] = Number(item[yAxis.field] || 0);
        });
      }

      return transformedItem;
    });
  }

  // Check if we need multi-series transformation for bar charts and line charts
  if ((graph.type === "bar" || graph.type === "line") && "y" in graph) {
    // Look for a potential series field (like 'model' in your case)
    // Common series field names to look for
    const potentialSeriesFields = ["model", "version_model", "agent_id", "type", "category"];
    const seriesField = availableKeys.find(
      (key) => potentialSeriesFields.includes(key) && key !== xAxisKey && key !== yAxisKey
    );

    // If we found a series field and have multiple unique values, use multi-series
    if (seriesField) {
      const uniqueSeriesValues = new Set(data.map((item) => String(item[seriesField] || "")));
      if (uniqueSeriesValues.size > 1) {
        // Transform data to multi-series format manually (similar to transformToMultiSeriesChartData)
        const grouped = new Map<string, Record<string, unknown>>();

        // Group data by x-axis values
        data.forEach((item) => {
          const xValue = String(item[xAxisKey] || "");
          const seriesValue = String(item[seriesField] || "");
          const yValue = Number(item[yAxisKey] || 0);

          if (!xValue || !seriesValue) return;

          if (!grouped.has(xValue)) {
            grouped.set(xValue, { x: xValue });
          }

          const groupedItem = grouped.get(xValue)!;
          groupedItem[seriesValue] = yValue;
        });

        // Convert to array and ensure all series have values for all x points
        const result = Array.from(grouped.values());
        const allSeriesValues = Array.from(uniqueSeriesValues);

        // Fill in missing values with 0
        result.forEach((item) => {
          allSeriesValues.forEach((seriesValue) => {
            if (!(seriesValue in item)) {
              item[seriesValue] = 0;
            }
          });
        });

        return result;
      }
    }
  }

  // Apply multi-series logic to BAR, LINE, and SCATTER charts that can benefit from it
  if (graph.type === "bar" || graph.type === "line" || graph.type === "scatter") {
    // Check if data has multiple numeric series (like your actor_movies_cost, movie_similarity_cost case)
    const numericKeys = availableKeys.filter((key) => {
      if (key === xAxisKey) return false;
      return data.some((item) => typeof item[key] === "number" && !isNaN(Number(item[key])));
    });

    // If we have multiple numeric series, preserve the structure for auto-detection
    if (numericKeys.length > 1) {
      return data.map((item) => {
        if (!item || typeof item !== "object") {
          return { x: "" };
        }

        return {
          ...item,
          x: String(item[xAxisKey] || ""),
        };
      });
    }
  }

  // For single series data or when we have explicit x/y configuration, use traditional approach
  return data.map((item) => {
    // Ensure item is a valid object
    if (!item || typeof item !== "object") {
      return { x: "", y: 0 };
    }

    return {
      x: String(item[xAxisKey] || ""),
      y: Number(item[yAxisKey] || 0),
    };
  });
}
