import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { CustomTooltip } from "./CustomTooltip";
import { DEFAULT_CHART_COLORS } from "./utils";

interface ChartData {
  x: string;
  y: number;
  [key: string]: unknown;
}

interface UniversalPieChartProps {
  data: ChartData[];
  tooltipFormatter?: (value: number) => string;
  colors?: string[];
  emptyMessage?: string;
  height?: string;
  fontSize?: number;
  disableAnimation?: boolean;
  showLegend?: boolean;
}

export function UniversalPieChart({
  data,
  tooltipFormatter = (value) => value.toString(),
  colors = DEFAULT_CHART_COLORS,
  emptyMessage = "No data available",
  fontSize = 12,
  disableAnimation = false,
  showLegend = true,
}: UniversalPieChartProps) {
  const mousePosRef = useRef({ x: 0, y: 0 });
  const [containerDimensions, setContainerDimensions] = useState({
    width: 400,
    height: 400,
  });
  const containerRef = useRef<HTMLDivElement>(null);

  // Measure actual container dimensions
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setContainerDimensions({
          width: rect.width || 400,
          height: rect.height || 400,
        });
      }
    };

    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  // Use a more direct approach - track all mouse moves over the entire container
  useEffect(() => {
    const handleGlobalMouseMove = (e: MouseEvent) => {
      const newPos = { x: e.clientX, y: e.clientY };
      mousePosRef.current = newPos;
      setMousePos(newPos);
    };

    const containerElement = containerRef.current;
    if (containerElement) {
      containerElement.addEventListener("mousemove", handleGlobalMouseMove);
      return () => {
        containerElement.removeEventListener(
          "mousemove",
          handleGlobalMouseMove
        );
      };
    }
  }, []);

  // State to force tooltip re-renders when mouse moves
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Update mouse position state for tooltip re-rendering
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const newPos = { x: e.clientX, y: e.clientY };
    mousePosRef.current = newPos;
    setMousePos(newPos);
  }, []);

  // Memoized tooltip content function that uses current mouse position
  const tooltipContent = useCallback(
    (props: {
      active?: boolean;
      payload?: Array<{ value: number; payload: { x: string; y: number } }>;
    }) => (
      <CustomTooltip
        {...props}
        mousePos={mousePos}
        formatter={tooltipFormatter}
        iconBorderRadius="50%"
      />
    ),
    [tooltipFormatter, mousePos]
  );

  // Memoized calculations for performance
  const { pieData, outerRadius, chartHeight } = useMemo(() => {
    if (data.length === 0) {
      return { pieData: [], outerRadius: 50, chartHeight: 200 };
    }

    // Calculate total for percentage display
    const total = data.reduce((sum, item) => sum + item.y, 0);

    // Transform data for pie chart with percentage
    const pieData = data.map((item) => ({
      ...item,
      name: item.x,
      value: item.y,
      percentage: ((item.y / total) * 100).toFixed(1),
    }));

    // Calculate responsive radius based on container width
    const { width } = containerDimensions;

    // Base the radius primarily on width since that's what constrains us in narrow containers
    const availableWidth = width - 80; // 40px padding on each side
    const maxRadius = availableWidth / 2 - 20; // 20px additional padding

    // Set reasonable bounds
    const minRadius = 50;
    const maxRadius_capped = Math.min(maxRadius, 200);

    const outerRadius = Math.max(minRadius, maxRadius_capped);

    // Calculate the chart height based on the actual pie size + padding
    // This ensures the chart container is just big enough for the pie + margins
    const chartHeight = outerRadius * 2 + 80; // 40px padding top and bottom

    return { pieData, outerRadius, chartHeight };
  }, [data, containerDimensions]);

  if (data.length === 0) {
    return <p className="text-gray-500 text-sm">{emptyMessage}</p>;
  }

  const renderCustomLabel = (props: { payload?: { percentage: string } }) => {
    if (!props.payload) return "";
    const percent = parseFloat(props.payload.percentage);
    // Only show label if segment is large enough (>3% of total)
    if (percent < 3) return "";
    return `${percent}%`;
  };

  return (
    <div
      ref={containerRef}
      className="flex-1 flex flex-col [&_.recharts-pie]:!opacity-100 [&_.recharts-pie:hover]:!opacity-100 [&_.recharts-wrapper]:!outline-none [&_.recharts-surface]:!outline-none [&_.recharts-tooltip-cursor]:!fill-transparent [&_.recharts-tooltip-item]:!text-gray-900 [&_.recharts-tooltip-item]:!font-medium [&_.recharts-tooltip-item]:text-[13px]"
      onMouseMove={handleMouseMove}
    >
      {/* Pie Chart Container - Dynamic height based on pie size */}
      <div className="flex-shrink-0" style={{ height: `${chartHeight}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomLabel}
              outerRadius={outerRadius}
              fill="#8884d8"
              dataKey="value"
              isAnimationActive={!disableAnimation}
              animationDuration={disableAnimation ? 0 : 400}
            >
              {pieData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={colors[index % colors.length]}
                  stroke="#fff"
                  strokeWidth={2}
                />
              ))}
            </Pie>
            <Tooltip
              content={tooltipContent}
              animationDuration={0}
              allowEscapeViewBox={{ x: true, y: true }}
              isAnimationActive={false}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Custom Legend Below Pie Chart - Now adds bonus height */}
      {showLegend && (
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 px-4 py-3 border-t border-gray-100">
          {pieData.map((entry, index) => (
            <div key={`legend-${index}`} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ backgroundColor: colors[index % colors.length] }}
              />
              <span
                className="text-gray-700 whitespace-nowrap"
                style={{ fontSize: `${fontSize}px` }}
              >
                {entry.name} ({entry.percentage}%)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
