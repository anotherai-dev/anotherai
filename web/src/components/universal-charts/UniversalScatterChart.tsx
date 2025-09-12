import { useCallback, useMemo, useRef } from "react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { CustomTooltip } from "./CustomTooltip";
import { SeriesConfig, autoDetectSeries, ensureXFieldForChart } from "./utils";

interface ChartData {
  x: string;
  y: number;
  [key: string]: unknown;
}

interface ScatterData {
  x: number;
  y: number;
  name: string;
  originalName?: string;
  [key: string]: unknown;
}

interface UniversalScatterChartProps {
  data: ChartData[];
  yAxisFormatter?: (value: number) => string;
  xAxisFormatter?: (value: number) => string;
  tooltipFormatter?: (value: number) => string;
  dotColor?: string; // For single series (backward compatibility)
  series?: SeriesConfig[]; // For multi-series
  showLegend?: boolean; // Whether to show legend
  emptyMessage?: string;
  height?: string;
  fontSize?: number;
  disableAnimation?: boolean;
  xAxisLabel?: string; // Label for X axis
  yAxisLabel?: string; // Label for Y axis
  xAxisUnit?: string; // Unit for X axis
  yAxisUnit?: string; // Unit for Y axis
}

export function UniversalScatterChart({
  data,
  yAxisFormatter = (value) => value.toString(),
  xAxisFormatter = (value) => value.toString(),
  tooltipFormatter = (value) => value.toString(),
  dotColor = "#EF4444",
  series,
  showLegend = true,
  emptyMessage = "No data available",
  height = "400px",
  fontSize = 12,
  disableAnimation = false,
  xAxisLabel,
  yAxisLabel,
  xAxisUnit,
  yAxisUnit,
}: UniversalScatterChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Transform data to ensure it has 'x' field (skip if already transformed by CompletionsGraph)
  const transformedData = useMemo(() => {
    // Check if data is already transformed by CompletionsGraph (has x field and is properly structured)
    if (data.length > 0 && data[0] && typeof data[0] === "object" && "x" in data[0]) {
      return data;
    }
    return ensureXFieldForChart(data);
  }, [data]);

  // Auto-detect series from transformed data if not provided (skip if already have series)
  const autoDetectedSeries = useMemo(() => {
    if (series && series.length > 0) {
      return series;
    }
    return autoDetectSeries(transformedData, series);
  }, [transformedData, series]);
  const isMultiSeries = series && series.length > 0;

  const finalSeries = useMemo(() => {
    return isMultiSeries ? series : autoDetectedSeries || [];
  }, [isMultiSeries, series, autoDetectedSeries]);

  const isActuallyMultiSeries = finalSeries.length > 0;

  // Get all series that have at least one defined value (including zero)
  const filteredSeries = useMemo(() => {
    if (!isActuallyMultiSeries) return (finalSeries || []).filter(Boolean);
    if (!finalSeries || !Array.isArray(finalSeries)) return [];

    return finalSeries
      .filter(Boolean) // Remove any undefined/null items
      .filter((seriesItem) => {
        if (!seriesItem || !seriesItem.key) return false;
        return transformedData.some((dataPoint) => {
          const value = dataPoint[seriesItem.key];
          return value !== undefined && value !== null;
        });
      });
  }, [finalSeries, isActuallyMultiSeries, transformedData]);

  // Axis tick formatters (no units on axis ticks)
  const xAxisTickFormatter = xAxisFormatter;
  const yAxisTickFormatter = yAxisFormatter;

  const tooltipFormatterWithUnit = useCallback(
    (value: number) => {
      const formattedValue = tooltipFormatter(value);
      return yAxisUnit ? `${formattedValue} ${yAxisUnit}` : formattedValue;
    },
    [tooltipFormatter, yAxisUnit]
  );

  // Create axis labels with units
  const xAxisLabelWithUnit = useMemo(() => {
    if (!xAxisLabel && !xAxisUnit) return undefined;
    if (xAxisLabel && xAxisUnit) return `${xAxisLabel} (${xAxisUnit})`;
    if (xAxisUnit) return xAxisUnit;
    return xAxisLabel;
  }, [xAxisLabel, xAxisUnit]);

  const yAxisLabelWithUnit = useMemo(() => {
    if (!yAxisLabel && !yAxisUnit) return undefined;
    if (yAxisLabel && yAxisUnit) return `${yAxisLabel} (${yAxisUnit})`;
    if (yAxisUnit) return yAxisUnit;
    return yAxisLabel;
  }, [yAxisLabel, yAxisUnit]);

  // Memoized canvas for text width measurement
  const measureTextWidth = useMemo(() => {
    if (!canvasRef.current && typeof document !== "undefined") {
      canvasRef.current = document.createElement("canvas");
    }

    return (text: string, fontSize: number): number => {
      const context = canvasRef.current?.getContext("2d");
      if (!context) return text.length * fontSize * 0.6; // Fallback

      context.font = `${fontSize}px Arial, sans-serif`;
      return context.measureText(text).width;
    };
  }, []);

  // Use a ref to track mouse position without causing re-renders
  const mousePosRef = useRef({ x: 0, y: 0 });

  // Memoized tooltip content function that uses ref instead of state
  const tooltipContent = useCallback(
    (props: { active?: boolean; payload?: Array<{ value: number; payload: ScatterData }> }) => {
      // Transform scatter chart payload to match CustomTooltip expectations
      if (props.active && props.payload && props.payload.length > 0) {
        const scatterData = props.payload[0].payload;
        const transformedPayload = [
          {
            value: scatterData.y,
            payload: { x: scatterData.originalName || scatterData.name }, // Use originalName for tooltip if available
            dataKey: String(scatterData.seriesName || "y"),
            color: String(scatterData.color || dotColor),
          },
        ];
        return (
          <CustomTooltip
            {...props}
            payload={transformedPayload}
            mousePos={mousePosRef.current}
            formatter={tooltipFormatterWithUnit}
            iconBorderRadius="50%"
            isChartMultiSeries={isActuallyMultiSeries}
          />
        );
      }
      return null;
    },
    [tooltipFormatterWithUnit, dotColor, isActuallyMultiSeries]
  );

  // Mouse move handler that updates ref without causing re-renders
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    mousePosRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  // Memoized data transformation and calculations
  const { scatterData, xMin, xMax, yMin, yMax, xPadding, yPadding, leftMargin } = useMemo(() => {
    if (transformedData.length === 0) {
      return {
        scatterData: [],
        xMin: 0,
        xMax: 1,
        yMin: 0,
        yMax: 1,
        xPadding: 0,
        yPadding: 0,
        leftMargin: 20,
      };
    }

    let scatterData: ScatterData[] = [];

    if (isActuallyMultiSeries) {
      // Multi-series: create scatter points for each series
      transformedData.forEach((item, dataIndex) => {
        const numericX = parseFloat(String(item.x));
        const xValue = isNaN(numericX) ? dataIndex : numericX;
        const originalName = String(item.x);
        const truncatedName = originalName.length > 20 ? originalName.substring(0, 20) + "..." : originalName;

        filteredSeries.forEach((seriesItem) => {
          const yValue = Number(item[seriesItem.key] || 0);

          scatterData.push({
            x: xValue,
            y: yValue,
            name: truncatedName,
            originalName: originalName,
            seriesName: seriesItem.name || seriesItem.key,
            seriesKey: seriesItem.key,
            color: seriesItem.color,
          });
        });
      });
    } else {
      // Single series: transform data for scatter chart
      scatterData = transformedData.map((item, index) => {
        // Try to parse x as number, fallback to index if it's not numeric
        const numericX = parseFloat(String(item.x));
        const originalName = String(item.x);
        const truncatedName = originalName.length > 20 ? originalName.substring(0, 20) + "..." : originalName;

        const transformedItem: ScatterData = {
          x: isNaN(numericX) ? index : numericX,
          y: Number(item.y || 0),
          name: truncatedName, // Use truncated name for display
          originalName: originalName, // Keep original for tooltip
        };

        // Add other properties from original item, excluding x and y to avoid conflicts
        Object.keys(item).forEach((key) => {
          if (key !== "x" && key !== "y") {
            (transformedItem as Record<string, unknown>)[key] = item[key];
          }
        });

        return transformedItem;
      });
    }

    // Calculate axis domains
    const xValues = scatterData.map((d) => d.x);
    const yValues = scatterData.map((d) => d.y);
    const xMin = Math.min(...xValues);
    const xMax = Math.max(...xValues);
    const yMin = Math.min(...yValues);
    const yMax = Math.max(...yValues);

    // Add some padding to the domains
    const xPadding = (xMax - xMin) * 0.1 || 1;
    const yPadding = (yMax - yMin) * 0.1 || 1;

    // Calculate left margin based on Y-axis label widths
    const yAxisLabels = [
      yAxisTickFormatter(yMin - yPadding),
      yAxisTickFormatter(yMax + yPadding),
      yAxisTickFormatter((yMin + yMax) / 2), // Middle value
    ];

    const maxYLabelWidth = Math.max(...yAxisLabels.map((label) => measureTextWidth(String(label), fontSize)));

    // Left margin: max label width + tick marks + some padding
    const leftMargin = Math.max(20, maxYLabelWidth + 5); // 5px for tick marks and spacing

    return {
      scatterData,
      xMin,
      xMax,
      yMin,
      yMax,
      xPadding,
      yPadding,
      leftMargin,
    };
  }, [transformedData, isActuallyMultiSeries, filteredSeries, yAxisTickFormatter, fontSize, measureTextWidth]);

  if (transformedData.length === 0) {
    return <p className="text-gray-500 text-sm">{emptyMessage}</p>;
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 [&_.recharts-scatter]:!opacity-100 [&_.recharts-scatter:hover]:!opacity-100 [&_.recharts-wrapper]:!outline-none [&_.recharts-surface]:!outline-none [&_.recharts-tooltip-cursor]:!fill-transparent [&_.recharts-tooltip-item]:!text-gray-900 [&_.recharts-tooltip-item]:!font-medium [&_.recharts-tooltip-item]:text-[13px]"
      onMouseMove={handleMouseMove}
      style={{ minHeight: height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart data={scatterData} margin={{ top: 20, right: 30, left: leftMargin, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            type="number"
            dataKey="x"
            domain={[xMin - xPadding, xMax + xPadding]}
            tick={{ fontSize: fontSize }}
            axisLine={{ stroke: "#e0e0e0" }}
            tickLine={{ stroke: "#e0e0e0" }}
            tickFormatter={xAxisTickFormatter}
            label={
              xAxisLabelWithUnit
                ? {
                    value: xAxisLabelWithUnit,
                    position: "insideBottom",
                    offset: -10,
                    style: {
                      textAnchor: "middle",
                      fontSize: fontSize,
                      fill: "#6b7280",
                    },
                  }
                : undefined
            }
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[yMin - yPadding, yMax + yPadding]}
            tick={{ fontSize: fontSize }}
            axisLine={{ stroke: "#e0e0e0" }}
            tickLine={{ stroke: "#e0e0e0" }}
            tickFormatter={yAxisTickFormatter}
            label={
              yAxisLabelWithUnit
                ? {
                    value: yAxisLabelWithUnit,
                    angle: -90,
                    position: "insideLeft",
                    style: {
                      textAnchor: "middle",
                      fontSize: fontSize,
                      fill: "#6b7280",
                    },
                  }
                : undefined
            }
          />
          <Tooltip
            content={tooltipContent}
            animationDuration={0}
            cursor={{ strokeDasharray: "3 3", stroke: "#d1d5db" }}
            allowEscapeViewBox={{ x: true, y: true }}
            isAnimationActive={false}
          />
          {filteredSeries.length > 0 ? (
            filteredSeries
              .filter((seriesItem) => seriesItem && seriesItem.key) // Extra safety check
              .map((seriesItem) => (
                <Scatter
                  key={seriesItem.key}
                  data={scatterData.filter((d) => d.seriesKey === seriesItem.key)}
                  fill={seriesItem.color}
                  name={seriesItem.name || seriesItem.key}
                  isAnimationActive={!disableAnimation}
                  animationDuration={disableAnimation ? 0 : 400}
                />
              ))
          ) : (
            <Scatter
              data={scatterData}
              fill={dotColor}
              isAnimationActive={!disableAnimation}
              animationDuration={disableAnimation ? 0 : 400}
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>

      {/* Legend Below Scatter Chart */}
      {showLegend && filteredSeries.length > 0 && (
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 px-4 py-3 border-t border-gray-100">
          {filteredSeries.map((seriesItem, index) => (
            <div key={`legend-${index}`} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: seriesItem.color }} />
              <span className="text-gray-700 whitespace-nowrap" style={{ fontSize: `${fontSize}px` }}>
                {seriesItem.name || seriesItem.key}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
