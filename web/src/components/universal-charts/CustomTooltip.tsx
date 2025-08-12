import { useEffect, useRef, useState } from "react";

export interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: { x: string };
    dataKey?: string;
    color?: string;
  }>;
  mousePos: { x: number; y: number };
  formatter: (value: number) => string;
  iconBorderRadius?: string; // '1px' for bars, '50%' for lines/dots
  isChartMultiSeries?: boolean; // Whether the chart itself is multi-series (not just current payload)
}

export const CustomTooltip = ({
  active,
  payload,
  mousePos,
  formatter,
  iconBorderRadius = "1px",
  isChartMultiSeries = false,
}: CustomTooltipProps) => {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [tooltipPosition, setTooltipPosition] = useState({
    x: mousePos.x,
    y: mousePos.y - 60,
  });

  useEffect(() => {
    if (active && payload && payload.length && tooltipRef.current) {
      const tooltipElement = tooltipRef.current;
      const tooltipRect = tooltipElement.getBoundingClientRect();
      const viewportWidth = window.innerWidth;

      let newX = mousePos.x;
      let newY = mousePos.y - tooltipRect.height - 10;

      // Adjust horizontal position if tooltip goes off-screen
      if (newX + tooltipRect.width / 2 > viewportWidth - 10) {
        newX = viewportWidth - tooltipRect.width / 2 - 10;
      } else if (newX - tooltipRect.width / 2 < 10) {
        newX = tooltipRect.width / 2 + 10;
      }

      // Adjust vertical position if tooltip goes off-screen
      if (newY < 10) {
        newY = mousePos.y + 20; // Show below cursor if no room above
      }

      setTooltipPosition({ x: newX, y: newY });
    }
  }, [active, payload, mousePos]);

  if (active && payload && payload.length) {
    const isMultiSeries = isChartMultiSeries || payload.length > 1;

    return (
      <div
        ref={tooltipRef}
        style={{
          position: "fixed",
          left: tooltipPosition.x,
          top: tooltipPosition.y,
          transform: "translateX(-50%)",
          backgroundColor: "#fff",
          border: "1px solid #e0e0e0",
          borderRadius: "2px",
          padding: "6px 10px",
          fontSize: "13px",
          color: "#111827",
          fontWeight: "500",
          pointerEvents: "none",
          zIndex: 1000,
          boxShadow:
            "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
          textAlign: isMultiSeries ? "left" : "center",
          minWidth: isMultiSeries ? "120px" : "auto",
          maxWidth: "300px",
        }}
      >
        <div
          style={{
            fontSize: "11px",
            color: "#6b7280",
            marginBottom: isMultiSeries ? "4px" : "2px",
            textAlign: "center",
          }}
        >
          {payload[0].payload.x}
        </div>
        {isMultiSeries ? (
          payload.map((entry, index) => (
            <div
              key={index}
              style={{
                display: "flex",
                alignItems: "center",
                marginBottom: index < payload.length - 1 ? "2px" : "0",
              }}
            >
              <div
                style={{
                  width: "8px",
                  height: "8px",
                  backgroundColor: entry.color,
                  marginRight: "6px",
                  borderRadius: iconBorderRadius,
                }}
              />
              <span style={{ fontSize: "12px" }}>
                {entry.dataKey || "Unknown"}: {formatter(entry.value)}
              </span>
            </div>
          ))
        ) : (
          <div>{formatter(payload[0].value)}</div>
        )}
      </div>
    );
  }
  return null;
};
