"use client";

import { useMemo } from "react";
import { Error, Graph, YAxis } from "@/types/models";
import { UniversalBarChart } from "./UniversalBarChart";
import { UniversalLineChart } from "./UniversalLineChart";
import { UniversalPieChart } from "./UniversalPieChart";
import { UniversalScatterChart } from "./UniversalScatterChart";
import { transformDataForCompletionsGraph } from "./utils";

interface CompletionsGraphProps {
  data: Record<string, unknown>[];
  isLoading: boolean;
  error: Error | null;
  graph: Graph;
  title?: string;
  showBorder?: boolean;
}

// Generate series configuration from Y axes with golden angle color distribution
function createSeriesFromYAxes(yAxes: YAxis[]) {
  return yAxes.map((yAxis, index) => ({
    key: yAxis.field,
    color: yAxis.color_hex || `hsl(${index * 137.508}deg 80% 50%)`, // Golden angle distribution for colors
    name: yAxis.label || yAxis.field,
    unit: yAxis.unit, // Pass through the unit for per-series formatting
  }));
}

export function CompletionsGraph({ data, isLoading, error, graph, showBorder = true }: CompletionsGraphProps) {
  // Memoized and optimized data transformation using utils function
  const chartData = useMemo(() => {
    return transformDataForCompletionsGraph({ data, graph });
  }, [data, graph]);

  if (isLoading) {
    return (
      <div className={`bg-white ${showBorder ? "border border-gray-200" : ""} rounded-[2px] flex flex-col p-6`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white ${showBorder ? "border border-gray-200" : ""} rounded-[2px] flex flex-col p-6`}>
        <div className="text-red-600 text-center">
          <p className="font-semibold">Error loading chart</p>
          <p className="text-sm mt-2">{error?.error || "Unknown error"}</p>
        </div>
      </div>
    );
  }
  const primaryColor = ("y" in graph && graph.y?.[0]?.color_hex) || "#3B82F6";

  // Extract axis labels and units from graph configuration
  const xAxisLabel = "x" in graph ? graph.x?.label : undefined;
  const yAxisLabel = "y" in graph ? graph.y?.[0]?.label : undefined;
  const xAxisUnit = "x" in graph ? graph.x?.unit : undefined;
  const yAxisUnit = "y" in graph ? graph.y?.[0]?.unit : undefined;

  const renderChart = () => {
    const commonProps = {
      data: chartData as { x: string; y: number; [key: string]: unknown }[],
      emptyMessage: "No data available for this chart",
      height: "600px",
      fontSize: 14,
      disableAnimation: true,
      xAxisLabel,
      yAxisLabel,
      xAxisUnit,
      yAxisUnit,
    };

    switch (graph.type) {
      case "bar":
        return (
          <UniversalBarChart
            {...commonProps}
            barColor={primaryColor}
            stackedBars={("stacked" in graph ? graph.stacked : false) as boolean}
          />
        );

      case "line":
        // Check if we have multiple Y axes defined
        if ("y" in graph && graph.y && graph.y.length > 1) {
          // Create series config for multi-Y line chart
          const series = createSeriesFromYAxes(graph.y);

          return <UniversalLineChart {...commonProps} series={series} showLegend={true} />;
        } else {
          // Single Y axis - let UniversalLineChart handle multi-series detection automatically
          return <UniversalLineChart {...commonProps} lineColor={primaryColor} />;
        }

      case "pie":
        // Pie charts don't use axis labels, so create props without them
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { xAxisLabel: _, yAxisLabel: __, ...pieProps } = commonProps;
        return (
          <UniversalPieChart
            {...pieProps}
            colors={[primaryColor, "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]}
            showLegend={true}
          />
        );

      case "scatter":
        return <UniversalScatterChart {...commonProps} dotColor={primaryColor} />;

      default:
        return (
          <UniversalBarChart
            {...commonProps}
            barColor={primaryColor}
            stackedBars={("stacked" in graph ? graph.stacked : false) as boolean}
          />
        );
    }
  };

  return (
    <div className={`bg-white ${showBorder ? "border border-gray-200" : ""} rounded-[2px] flex flex-col pt-6`}>
      {renderChart()}
    </div>
  );
}
