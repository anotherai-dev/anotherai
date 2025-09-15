import { useCallback } from "react";
import { SeriesConfig, formatValueWithUnit } from "./utils";

/**
 * Custom hook for creating a tooltip formatter that supports per-series units
 * @param tooltipFormatter - Base formatter function for values
 * @param yAxisUnit - Global Y-axis unit (fallback)
 * @param isActuallyMultiSeries - Whether the chart has multiple series
 * @param series - Array of series configurations with units
 * @returns Memoized formatter function that handles per-series units
 */
export function useTooltipFormatterWithUnit(
  tooltipFormatter: (value: number) => string,
  yAxisUnit: string | undefined,
  isActuallyMultiSeries: boolean,
  series: SeriesConfig[] | null | undefined
) {
  return useCallback(
    (value: number, seriesKey?: string) => {
      const formattedValue = tooltipFormatter(value);

      // If we have series and a series key, try to find the unit for this specific series
      if (isActuallyMultiSeries && seriesKey && series) {
        const foundSeries = series.find((s) => s.key === seriesKey);
        if (foundSeries?.unit) {
          return formatValueWithUnit(formattedValue, foundSeries.unit);
        }
      }

      // Fallback to the global yAxisUnit (for backward compatibility)
      return yAxisUnit ? formatValueWithUnit(formattedValue, yAxisUnit) : formattedValue;
    },
    [tooltipFormatter, yAxisUnit, isActuallyMultiSeries, series]
  );
}
