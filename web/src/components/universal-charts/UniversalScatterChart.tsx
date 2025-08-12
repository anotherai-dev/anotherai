import { useCallback, useMemo, useRef } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CustomTooltip } from "./CustomTooltip";

interface ChartData {
  x: string;
  y: number;
  [key: string]: unknown;
}

interface ScatterData {
  x: number;
  y: number;
  name: string;
  [key: string]: unknown;
}

interface UniversalScatterChartProps {
  data: ChartData[];
  yAxisFormatter?: (value: number) => string;
  xAxisFormatter?: (value: number) => string;
  tooltipFormatter?: (value: number) => string;
  dotColor?: string;
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
    if (!canvasRef.current) {
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
    (props: {
      active?: boolean;
      payload?: Array<{ value: number; payload: ScatterData }>;
    }) => {
      // Transform scatter chart payload to match CustomTooltip expectations
      if (props.active && props.payload && props.payload.length > 0) {
        const scatterData = props.payload[0].payload;
        const transformedPayload = [
          {
            value: scatterData.y,
            payload: { x: scatterData.name }, // Use name (original x value) for display
            dataKey: "y",
            color: dotColor,
          },
        ];
        return (
          <CustomTooltip
            {...props}
            payload={transformedPayload}
            mousePos={mousePosRef.current}
            formatter={tooltipFormatterWithUnit}
            iconBorderRadius="50%"
          />
        );
      }
      return null;
    },
    [tooltipFormatterWithUnit, dotColor]
  );

  // Mouse move handler that updates ref without causing re-renders
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    mousePosRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  // Memoized data transformation and calculations
  const {
    scatterData,
    xMin,
    xMax,
    yMin,
    yMax,
    xPadding,
    yPadding,
    leftMargin,
  } = useMemo(() => {
    if (data.length === 0) {
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
    // Transform data for scatter chart
    // For scatter charts, we need numeric x values, so we'll convert or use index
    const scatterData: ScatterData[] = data.map((item, index) => {
      // Try to parse x as number, fallback to index if it's not numeric
      const numericX = parseFloat(String(item.x));
      const transformedItem: ScatterData = {
        x: isNaN(numericX) ? index : numericX,
        y: item.y,
        name: String(item.x), // Keep original x as name for display
      };

      // Add other properties from original item, excluding x and y to avoid conflicts
      Object.keys(item).forEach((key) => {
        if (key !== "x" && key !== "y") {
          (transformedItem as Record<string, unknown>)[key] = item[key];
        }
      });

      return transformedItem;
    });

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

    const maxYLabelWidth = Math.max(
      ...yAxisLabels.map((label) => measureTextWidth(String(label), fontSize))
    );

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
  }, [data, yAxisTickFormatter, fontSize, measureTextWidth]);

  if (data.length === 0) {
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
        <ScatterChart
          data={scatterData}
          margin={{ top: 20, right: 30, left: leftMargin, bottom: 40 }}
        >
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
          <Scatter
            data={scatterData}
            fill={dotColor}
            isAnimationActive={!disableAnimation}
            animationDuration={disableAnimation ? 0 : 400}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
