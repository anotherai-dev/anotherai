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
  height = "400px",
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

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    mousePosRef.current = { x: e.clientX, y: e.clientY };
  }, []);

  // Memoized tooltip content function that uses ref instead of state
  const tooltipContent = useCallback(
    (props: {
      active?: boolean;
      payload?: Array<{ value: number; payload: { x: string; y: number } }>;
    }) => (
      <CustomTooltip
        {...props}
        mousePos={mousePosRef.current}
        formatter={tooltipFormatter}
        iconBorderRadius="50%"
      />
    ),
    [tooltipFormatter]
  );

  // Memoized calculations for performance
  const { pieData, outerRadius } = useMemo(() => {
    if (data.length === 0) {
      return { pieData: [], outerRadius: 50 };
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

    // Calculate responsive radius based on container size
    const { width, height } = containerDimensions;

    // Since we now have proper flexbox layout, we can be more generous with the pie chart size
    // The legend is handled separately and won't interfere
    const availableWidth = width - 60; // 30px padding on each side
    const availableHeight = height - 60; // 30px padding top and bottom

    // Use the smaller dimension to ensure the pie fits
    const maxRadius = Math.min(availableWidth, availableHeight) / 2 - 20; // 20px additional padding

    // Set reasonable bounds
    const minRadius = 50;
    const maxRadius_capped = Math.min(maxRadius, 200); // Allow larger pies now

    const outerRadius = Math.max(minRadius, maxRadius_capped);

    return { pieData, outerRadius };
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
      style={{ minHeight: height }}
    >
      {/* Pie Chart Container */}
      <div className="flex-1 min-h-0">
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

      {/* Custom Legend Below Pie Chart */}
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
