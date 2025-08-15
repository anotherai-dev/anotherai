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

  // Auto-detect series from non-x/y keys
  const seriesKeys = keys.filter((key) => key !== "x" && key !== "y");

  if (seriesKeys.length === 0) {
    return [];
  }

  return seriesKeys.map((key, index) => ({
    key,
    color: DEFAULT_CHART_COLORS[index % DEFAULT_CHART_COLORS.length],
    name: key,
  }));
}
