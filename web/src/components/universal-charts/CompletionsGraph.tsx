"use client";

import { transformToMultiSeriesChartData } from "@/components/utils/utils";
import { Error, Graph, YAxis } from "@/types/models";
import { UniversalBarChart } from "./UniversalBarChart";
import { UniversalLineChart } from "./UniversalLineChart";
import { UniversalPieChart } from "./UniversalPieChart";
import { UniversalScatterChart } from "./UniversalScatterChart";

// Helper function to determine X-axis key from graph configuration
function getXAxisKey(graph: Graph, availableKeys: string[]): string {
  if ("x" in graph && graph.x?.field) {
    return graph.x.field;
  }
  return availableKeys[0];
}

// Helper function to determine Y-axis key from graph configuration
function getYAxisKey(graph: Graph, availableKeys: string[], xAxisKey: string): string {
  if ("y" in graph && graph.y?.[0]?.field) {
    return graph.y[0].field;
  }

  // Find first key that's different from xAxisKey, or fallback to first key
  const alternativeKey = availableKeys.find((key) => key !== xAxisKey);
  return alternativeKey || availableKeys[0];
}

interface CompletionsGraphProps {
  data: Record<string, unknown>[];
  isLoading: boolean;
  error: Error | null;
  graph: Graph;
  title?: string;
}

// Generate series configuration from Y axes with golden angle color distribution
function createSeriesFromYAxes(yAxes: YAxis[]) {
  return yAxes.map((yAxis, index) => ({
    key: yAxis.field,
    color: yAxis.color_hex || `hsl(${index * 137.508}deg 80% 50%)`, // Golden angle distribution for colors
    name: yAxis.label || yAxis.field,
  }));
}

export function CompletionsGraph({ data, isLoading, error, graph }: CompletionsGraphProps) {
  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-[2px] flex flex-col p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-gray-200 rounded-[2px] flex flex-col p-6">
        <div className="text-red-600 text-center">
          <p className="font-semibold">Error loading chart</p>
          <p className="text-sm mt-2">{error?.error || "Unknown error"}</p>
        </div>
      </div>
    );
  }

  // Transform data for chart format
  const transformDataForChart = () => {
    if (!data || data.length === 0) return [];

    // Safely get first item to extract keys
    const firstItem = data[0];
    if (!firstItem || typeof firstItem !== "object") return [];

    const availableKeys = Object.keys(firstItem);
    if (availableKeys.length === 0) return [];

    const xAxisKey = getXAxisKey(graph, availableKeys);
    const yAxisKey = getYAxisKey(graph, availableKeys, xAxisKey);

    // Check if we have multiple Y axes defined (for line charts)
    if (graph.type === "line" && "y" in graph && graph.y && graph.y.length > 1) {
      // Multi-Y axis line chart - transform data to include multiple Y series
      return data.map((item) => {
        if (!item || typeof item !== "object") {
          return { x: "" };
        }

        const transformedItem: Record<string, unknown> = {
          x: String(item[xAxisKey] || ""),
        };

        // Add each Y axis as a separate series
        if ("y" in graph && graph.y) {
          graph.y.forEach((yAxis) => {
            transformedItem[yAxis.field] = Number(item[yAxis.field] || 0);
          });
        }

        return transformedItem;
      });
    }

    // Check if we need multi-series transformation for bar charts and line charts
    if ((graph.type === "bar" || graph.type === "line") && "y" in graph) {
      // Look for a potential series field (like 'model' in your case)
      // Common series field names to look for
      const potentialSeriesFields = ["model", "version_model", "agent_id", "type", "category"];
      const seriesField = availableKeys.find(
        (key) => potentialSeriesFields.includes(key) && key !== xAxisKey && key !== yAxisKey
      );

      // If we found a series field and have multiple unique values, use multi-series
      if (seriesField) {
        const uniqueSeriesValues = new Set(data.map((item) => String(item[seriesField] || "")));
        if (uniqueSeriesValues.size > 1) {
          return transformToMultiSeriesChartData(data, xAxisKey, yAxisKey, seriesField);
        }
      }
    }

    // Fallback to single series format (for other chart types or single series data)
    return data.map((item) => {
      // Ensure item is a valid object
      if (!item || typeof item !== "object") {
        return { x: "", y: 0 };
      }

      return {
        x: String(item[xAxisKey] || ""),
        y: Number(item[yAxisKey] || 0),
        // Don't include ...item to avoid conflicts with multi-series detection
      };
    });
  };

  const chartData = transformDataForChart();
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

  return <div className="bg-white border border-gray-200 rounded-[2px] flex flex-col pt-6">{renderChart()}</div>;
}
