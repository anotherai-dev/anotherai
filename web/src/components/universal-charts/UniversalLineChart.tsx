import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CustomTooltip } from "./CustomTooltip";
import { useTooltipFormatterWithUnit } from "./useTooltipFormatterWithUnit";
import { SeriesConfig, autoDetectSeries, ensureXFieldForChart } from "./utils";

interface ChartData {
  x: string;
  y?: number; // For single series (backward compatibility)
  [key: string]: unknown; // For multi-series data
}

interface UniversalLineChartProps {
  data: ChartData[];
  yAxisFormatter?: (value: number) => string;
  tooltipFormatter?: (value: number) => string;
  lineColor?: string; // For single series (backward compatibility)
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

// Static stroke color for axis lines
const AXIS_STROKE_COLOR = "#e0e0e0";

// Global canvas for text measurement (shared across all chart instances)
let globalCanvas: HTMLCanvasElement | null = null;

// Text measurement cache
const textMeasurementCache = new Map<string, number>();

export function UniversalLineChart({
  data,
  yAxisFormatter = (value) => value.toString(),
  tooltipFormatter = (value) => value.toString(),
  lineColor = "#8B5CF6",
  series,
  showLegend = true,
  emptyMessage = "No data available",
  height = "200px",
  fontSize = 12,
  disableAnimation = false,
  xAxisLabel,
  yAxisLabel,
  xAxisUnit,
  yAxisUnit,
}: UniversalLineChartProps) {
  const [containerWidth, setContainerWidth] = useState(800);
  const containerRef = useRef<HTMLDivElement>(null);

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

  // Y-axis tick formatter (no units on axis ticks)
  const yAxisTickFormatter = yAxisFormatter;

  const tooltipFormatterWithUnit = useTooltipFormatterWithUnit(
    tooltipFormatter,
    yAxisUnit,
    isActuallyMultiSeries,
    finalSeries
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

  // Transform data to include zero values and truncate long labels
  const processedData = useMemo(() => {
    const processData = (inputData: ChartData[]) => {
      return inputData.map((dataPoint) => {
        const originalX = String(dataPoint.x);
        const truncatedX = originalX.length > 20 ? originalX.substring(0, 20) + "..." : originalX;

        const newDataPoint: Record<string, unknown> = {
          x: truncatedX,
          originalX: originalX, // Keep original for tooltip
        };

        if (!isActuallyMultiSeries) {
          // Single series - just copy y value
          newDataPoint.y = dataPoint.y;
          return newDataPoint;
        }

        // Multi-series - add all series values, including zeros
        filteredSeries.forEach((seriesItem) => {
          const value = Number(dataPoint[seriesItem.key] || 0);
          newDataPoint[seriesItem.key] = value;
        });

        return newDataPoint;
      });
    };

    return processData(transformedData as ChartData[]);
  }, [transformedData, isActuallyMultiSeries, filteredSeries]);

  // Measure actual container width with debouncing
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const updateWidth = () => {
      if (containerRef.current) {
        const width = containerRef.current.offsetWidth;
        const newWidth = width - 60; // Account for margins (left: 20, right: 30, padding)

        // Only update if width changed significantly to prevent micro-adjustments
        setContainerWidth((prev) => (Math.abs(prev - newWidth) > 5 ? newWidth : prev));
      }
    };

    const debouncedUpdateWidth = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(updateWidth, 100);
    };

    updateWidth();
    window.addEventListener("resize", debouncedUpdateWidth);
    return () => {
      window.removeEventListener("resize", debouncedUpdateWidth);
      clearTimeout(timeoutId);
    };
  }, []);

  // Initialize global canvas on first use
  useEffect(() => {
    if (!globalCanvas) {
      globalCanvas = document.createElement("canvas");
    }
  }, []);

  // Optimized text width measurement with caching
  const measureTextWidth = useCallback((text: string, fontSize: number): number => {
    const cacheKey = `${text}-${fontSize}`;

    // Check cache first
    if (textMeasurementCache.has(cacheKey)) {
      return textMeasurementCache.get(cacheKey)!;
    }

    // Fallback if canvas not available
    if (!globalCanvas) {
      const fallbackWidth = text.length * fontSize * 0.6;
      textMeasurementCache.set(cacheKey, fallbackWidth);
      return fallbackWidth;
    }

    const context = globalCanvas.getContext("2d");
    if (!context) {
      const fallbackWidth = text.length * fontSize * 0.6;
      textMeasurementCache.set(cacheKey, fallbackWidth);
      return fallbackWidth;
    }

    context.font = `${fontSize}px Arial, sans-serif`;
    const width = context.measureText(text).width;

    // Cache the result
    textMeasurementCache.set(cacheKey, width);

    // Prevent cache from growing too large
    if (textMeasurementCache.size > 1000) {
      const firstKey = textMeasurementCache.keys().next().value;
      if (firstKey !== undefined) {
        textMeasurementCache.delete(firstKey);
      }
    }

    return width;
  }, []);

  // Memoized label strategy calculation and chart height
  const {
    shouldRotate,
    interval,
    bottomMargin,
    leftMargin,
    rightMargin,
    tickStyle,
    axisLineStyle,
    tickLineStyle,
    chartHeight,
  } = useMemo(() => {
    if (transformedData.length <= 1)
      return {
        shouldRotate: false,
        interval: 0,
        bottomMargin: 40,
        leftMargin: 20,
        rightMargin: 30,
        tickStyle: { fontSize: fontSize },
        axisLineStyle: { stroke: AXIS_STROKE_COLOR },
        tickLineStyle: { stroke: AXIS_STROKE_COLOR },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };

    // For line charts, we need extra space to account for labels at the edges
    const availableWidthPerPoint = containerWidth / transformedData.length;

    // Measure the widest label using truncated labels
    const maxLabelWidth = Math.max(
      ...transformedData.map((item) => {
        const originalLabel = String(item.x);
        const truncatedLabel = originalLabel.length > 20 ? originalLabel.substring(0, 20) + "..." : originalLabel;
        return measureTextWidth(truncatedLabel, fontSize);
      })
    );

    const labelPadding = 8; // Minimum space between labels
    const totalHorizontalSpace = maxLabelWidth + labelPadding;

    // Calculate margins based on label width - line charts need more margin for edge labels
    const leftMargin = Math.max(20, maxLabelWidth / 4 + 10); // Less margin on left
    const rightMargin = Math.max(30, maxLabelWidth / 2 + 10); // Keep right margin generous

    // Try horizontal first
    if (totalHorizontalSpace <= availableWidthPerPoint) {
      return {
        shouldRotate: false,
        interval: 0,
        bottomMargin: Math.max(50, fontSize + 30), // fontSize + padding for axis and ticks
        leftMargin,
        rightMargin,
        tickStyle: { fontSize: fontSize },
        axisLineStyle: { stroke: AXIS_STROKE_COLOR },
        tickLineStyle: { stroke: AXIS_STROKE_COLOR },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };
    }

    // Try with rotation - labels need less horizontal space when angled
    const rotatedHorizontalSpace = maxLabelWidth * 0.7 + labelPadding; // ~70% of width when rotated 45°
    if (rotatedHorizontalSpace <= availableWidthPerPoint) {
      // For 45° rotated text: vertical space = sin(45°) * textWidth + cos(45°) * fontSize
      // sin(45°) ≈ 0.707, cos(45°) ≈ 0.707
      const textVertical = maxLabelWidth * 0.707; // horizontal text width projected vertically
      const fontVertical = fontSize * 0.707; // font height projected vertically
      const totalVertical = textVertical + fontVertical + 25; // extra padding for tick marks and spacing

      // For rotated labels, we need even more side margin
      const rotatedLeftMargin = Math.max(25, maxLabelWidth * 0.3 + 10); // Less margin on left
      const rotatedRightMargin = Math.max(40, maxLabelWidth * 0.5 + 15); // Keep right margin generous

      return {
        shouldRotate: true,
        interval: 0,
        bottomMargin: Math.max(80, Math.ceil(totalVertical)),
        leftMargin: rotatedLeftMargin,
        rightMargin: rotatedRightMargin,
        tickStyle: { fontSize: Math.max(fontSize - 1, 10) },
        axisLineStyle: { stroke: AXIS_STROKE_COLOR },
        tickLineStyle: { stroke: AXIS_STROKE_COLOR },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };
    }

    // Need to skip labels - calculate how many we can show
    const maxLabelsHorizontal = Math.floor(containerWidth / totalHorizontalSpace);
    const maxLabelsRotated = Math.floor(containerWidth / rotatedHorizontalSpace);

    if (maxLabelsRotated > maxLabelsHorizontal) {
      // Use rotation with interval
      const interval = Math.max(0, Math.ceil(transformedData.length / maxLabelsRotated) - 1);
      const textVertical = maxLabelWidth * 0.707;
      const fontVertical = fontSize * 0.707;
      const totalVertical = textVertical + fontVertical + 25;
      const rotatedLeftMargin = Math.max(25, maxLabelWidth * 0.3 + 10);
      const rotatedRightMargin = Math.max(40, maxLabelWidth * 0.5 + 15);

      return {
        shouldRotate: true,
        interval,
        bottomMargin: Math.max(80, Math.ceil(totalVertical)),
        leftMargin: rotatedLeftMargin,
        rightMargin: rotatedRightMargin,
        tickStyle: { fontSize: Math.max(fontSize - 1, 10) },
        axisLineStyle: { stroke: AXIS_STROKE_COLOR },
        tickLineStyle: { stroke: AXIS_STROKE_COLOR },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };
    } else {
      // Use horizontal with interval
      const interval = Math.max(0, Math.ceil(transformedData.length / maxLabelsHorizontal) - 1);
      return {
        shouldRotate: false,
        interval,
        bottomMargin: Math.max(50, fontSize + 30), // fontSize + padding for axis and ticks
        leftMargin,
        rightMargin,
        tickStyle: { fontSize: fontSize },
        axisLineStyle: { stroke: AXIS_STROKE_COLOR },
        tickLineStyle: { stroke: AXIS_STROKE_COLOR },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };
    }
  }, [transformedData, containerWidth, fontSize, measureTextWidth, height]);

  // Use a ref to track mouse position without causing re-renders
  const mousePosRef = useRef({ x: 0, y: 0 });

  // Memoized tooltip content function that uses ref instead of state
  const tooltipContent = useCallback(
    (props: {
      active?: boolean;
      payload?: Array<{
        value: number;
        payload: { x: string; originalX: string };
      }>;
    }) => {
      // Use originalX in tooltip if available, otherwise fall back to x
      const modifiedProps = {
        ...props,
        payload: props.payload?.map((item) => ({
          ...item,
          payload: {
            ...item.payload,
            x: item.payload.originalX || item.payload.x,
          },
        })),
      };

      return (
        <CustomTooltip
          {...modifiedProps}
          mousePos={mousePosRef.current}
          formatter={tooltipFormatterWithUnit}
          iconBorderRadius="50%"
          isChartMultiSeries={isActuallyMultiSeries}
        />
      );
    },
    [tooltipFormatterWithUnit, isActuallyMultiSeries]
  );

  // Mouse move handler that updates ref without causing re-renders
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    mousePosRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  if (transformedData.length === 0) {
    return <p className="text-gray-500 text-sm">{emptyMessage}</p>;
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 flex flex-col [&_.recharts-line]:!opacity-100 [&_.recharts-line:hover]:!opacity-100 [&_.recharts-wrapper]:!outline-none [&_.recharts-surface]:!outline-none [&_.recharts-tooltip-cursor]:!fill-transparent [&_.recharts-tooltip-item]:!text-gray-900 [&_.recharts-tooltip-item]:!font-medium [&_.recharts-tooltip-item]:text-[13px]"
      onMouseMove={handleMouseMove}
    >
      {/* Line Chart Container - Fixed height so legend doesn't interfere */}
      <div className="flex-shrink-0" style={{ height: `${chartHeight}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={processedData} margin={{ top: 5, right: rightMargin, left: leftMargin, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="x"
              tick={tickStyle}
              axisLine={axisLineStyle}
              tickLine={tickLineStyle}
              interval={interval}
              angle={shouldRotate ? -45 : 0}
              textAnchor={shouldRotate ? "end" : "middle"}
              height={bottomMargin}
              tickMargin={shouldRotate ? 10 : 5}
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
              tick={{ fontSize: fontSize }}
              axisLine={{ stroke: AXIS_STROKE_COLOR }}
              tickLine={{ stroke: AXIS_STROKE_COLOR }}
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
              cursor={false}
              allowEscapeViewBox={{ x: true, y: true }}
              isAnimationActive={false}
            />
            {filteredSeries.length > 0 ? (
              filteredSeries
                .filter((seriesItem) => seriesItem && seriesItem.key) // Extra safety check
                .map((seriesItem) => (
                  <Line
                    key={seriesItem.key}
                    type="monotone"
                    dataKey={seriesItem.key}
                    name={seriesItem.name || seriesItem.key}
                    stroke={seriesItem.color}
                    strokeWidth={2}
                    dot={{ fill: seriesItem.color, strokeWidth: 2, r: 4 }}
                    activeDot={{
                      r: 6,
                      stroke: seriesItem.color,
                      strokeWidth: 2,
                      fill: "#fff",
                    }}
                    isAnimationActive={!disableAnimation}
                    animationDuration={disableAnimation ? 0 : 400}
                  />
                ))
            ) : (
              <Line
                type="monotone"
                dataKey="y"
                stroke={lineColor}
                strokeWidth={2}
                dot={{ fill: lineColor, strokeWidth: 2, r: 4 }}
                activeDot={{
                  r: 6,
                  stroke: lineColor,
                  strokeWidth: 2,
                  fill: "#fff",
                }}
                isAnimationActive={!disableAnimation}
                animationDuration={disableAnimation ? 0 : 400}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend Below Line Chart - Now adds bonus height */}
      {showLegend && filteredSeries.length > 0 && (
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 px-4 py-3 border-t border-gray-100">
          {filteredSeries.map((seriesItem, index) => (
            <div key={`legend-${index}`} className="flex items-center gap-2">
              <div className="w-3 h-[2px] flex-shrink-0" style={{ backgroundColor: seriesItem.color }} />
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
