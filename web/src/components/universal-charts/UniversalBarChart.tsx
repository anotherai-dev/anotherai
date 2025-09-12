import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CustomTooltip } from "./CustomTooltip";
import { SeriesConfig, autoDetectSeries, ensureXFieldForChart } from "./utils";

interface ChartData {
  x: string;
  y?: number; // For single series (backward compatibility)
  [key: string]: unknown; // For multi-series data
}

interface UniversalBarChartProps {
  data: ChartData[];
  yAxisFormatter?: (value: number) => string;
  tooltipFormatter?: (value: number) => string;
  barColor?: string; // For single series (backward compatibility)
  series?: SeriesConfig[]; // For multi-series
  stackedBars?: boolean; // Whether to stack bars or group them
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

export function UniversalBarChart({
  data,
  yAxisFormatter = (value) => value.toString(),
  tooltipFormatter = (value) => value.toString(),
  barColor = "#3b82f6",
  series,
  stackedBars = false,
  showLegend = true,
  emptyMessage = "No data available",
  height = "200px",
  fontSize = 12,
  disableAnimation = false,
  xAxisLabel,
  yAxisLabel,
  xAxisUnit,
  yAxisUnit,
}: UniversalBarChartProps) {
  const [containerWidth, setContainerWidth] = useState(800);
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

  // Y-axis tick formatter (no units on axis ticks)
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

  // Get all series that have at least one non-zero value
  const filteredSeries = useMemo(() => {
    if (!isActuallyMultiSeries) return (finalSeries || []).filter(Boolean);
    if (!finalSeries || !Array.isArray(finalSeries)) return [];

    return finalSeries
      .filter(Boolean) // Remove any undefined/null items
      .filter((seriesItem) => {
        if (!seriesItem || !seriesItem.key) return false;
        return transformedData.some((dataPoint) => {
          const value = Number(dataPoint[seriesItem.key] || 0);
          return value > 0;
        });
      });
  }, [finalSeries, isActuallyMultiSeries, transformedData]);

  // Transform data to remove zero values completely and truncate long labels
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

        // Multi-series - only add series that have non-zero values for this data point
        filteredSeries.forEach((seriesItem) => {
          const value = Number(dataPoint[seriesItem.key] || 0);
          if (value > 0) {
            newDataPoint[seriesItem.key] = value;
          }
          // Don't add the series at all if value is 0
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

  // Memoized label strategy calculation and chart height
  const { shouldRotate, interval, bottomMargin, tickStyle, axisLineStyle, tickLineStyle, chartHeight } = useMemo(() => {
    if (transformedData.length <= 1)
      return {
        shouldRotate: false,
        interval: 0,
        bottomMargin: 40,
        tickStyle: { fontSize: fontSize },
        axisLineStyle: { stroke: "#e0e0e0" },
        tickLineStyle: { stroke: "#e0e0e0" },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };

    const availableWidthPerBar = containerWidth / transformedData.length;

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

    // Try horizontal first
    if (totalHorizontalSpace <= availableWidthPerBar) {
      return {
        shouldRotate: false,
        interval: 0,
        bottomMargin: Math.max(50, fontSize + 30), // fontSize + padding for axis and ticks
        tickStyle: { fontSize: fontSize },
        axisLineStyle: { stroke: "#e0e0e0" },
        tickLineStyle: { stroke: "#e0e0e0" },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };
    }

    // Try with rotation - labels need less horizontal space when angled
    const rotatedHorizontalSpace = maxLabelWidth * 0.7 + labelPadding; // ~70% of width when rotated 45°
    if (rotatedHorizontalSpace <= availableWidthPerBar) {
      // For 45° rotated text: vertical space = sin(45°) * textWidth + cos(45°) * fontSize
      // sin(45°) ≈ 0.707, cos(45°) ≈ 0.707
      const textVertical = maxLabelWidth * 0.707; // horizontal text width projected vertically
      const fontVertical = fontSize * 0.707; // font height projected vertically
      const totalVertical = textVertical + fontVertical + 25; // extra padding for tick marks and spacing

      return {
        shouldRotate: true,
        interval: 0,
        bottomMargin: Math.max(80, Math.ceil(totalVertical)),
        tickStyle: { fontSize: Math.max(fontSize - 1, 10) },
        axisLineStyle: { stroke: "#e0e0e0" },
        tickLineStyle: { stroke: "#e0e0e0" },
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

      return {
        shouldRotate: true,
        interval,
        bottomMargin: Math.max(80, Math.ceil(totalVertical)),
        tickStyle: { fontSize: Math.max(fontSize - 1, 10) },
        axisLineStyle: { stroke: "#e0e0e0" },
        tickLineStyle: { stroke: "#e0e0e0" },
        chartHeight: parseInt(height.replace("px", "")) || 200,
      };
    } else {
      // Use horizontal with interval
      const interval = Math.max(0, Math.ceil(transformedData.length / maxLabelsHorizontal) - 1);
      return {
        shouldRotate: false,
        interval,
        bottomMargin: Math.max(50, fontSize + 30), // fontSize + padding for axis and ticks
        tickStyle: { fontSize: fontSize },
        axisLineStyle: { stroke: "#e0e0e0" },
        tickLineStyle: { stroke: "#e0e0e0" },
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
          iconBorderRadius="1px"
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
      className="flex-1 flex flex-col [&_.recharts-bar]:!opacity-100 [&_.recharts-bar:hover]:!opacity-100 [&_.recharts-wrapper]:!outline-none [&_.recharts-surface]:!outline-none [&_.recharts-tooltip-cursor]:!fill-transparent [&_.recharts-tooltip-item]:!text-gray-900 [&_.recharts-tooltip-item]:!font-medium [&_.recharts-tooltip-item]:text-[13px]"
      onMouseMove={handleMouseMove}
    >
      {/* Bar Chart Container - Fixed height so legend doesn't interfere */}
      <div className="flex-shrink-0" style={{ height: `${chartHeight}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={processedData} margin={{ top: 5, right: 30, left: 20, bottom: 20 }}>
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
              cursor={false}
              allowEscapeViewBox={{ x: true, y: true }}
              isAnimationActive={false}
            />
            {filteredSeries.length > 0 ? (
              filteredSeries
                .filter((seriesItem) => seriesItem && seriesItem.key) // Extra safety check
                .map((seriesItem) => (
                  <Bar
                    key={seriesItem.key}
                    dataKey={seriesItem.key}
                    name={seriesItem.name || seriesItem.key}
                    fill={seriesItem.color}
                    radius={[2, 2, 0, 0]}
                    isAnimationActive={!disableAnimation}
                    animationDuration={disableAnimation ? 0 : 400}
                    stackId={stackedBars ? "stack" : undefined}
                  />
                ))
            ) : (
              <Bar
                dataKey="y"
                fill={barColor}
                radius={[2, 2, 0, 0]}
                isAnimationActive={!disableAnimation}
                animationDuration={disableAnimation ? 0 : 400}
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend Below Bar Chart - Now adds bonus height */}
      {showLegend && filteredSeries.length > 0 && (
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 px-4 py-3 border-t border-gray-100">
          {filteredSeries.map((seriesItem, index) => (
            <div key={`legend-${index}`} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: seriesItem.color }} />
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
