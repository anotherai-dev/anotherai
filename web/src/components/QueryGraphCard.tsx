"use client";

import { useMemo } from "react";
import { CompletionsGraph } from "@/components/universal-charts/CompletionsGraph";
import { useCompletionsQuery } from "@/store/completions";
import { Graph } from "@/types/models";

interface QueryGraphCardProps {
  title: string;
  subtitle: string;
  graphType: "bar" | "line" | "pie" | "scatter";
  query: string;
  customGraph?: Graph;
}

export function QueryGraphCard({ title, subtitle, graphType, query, customGraph }: QueryGraphCardProps) {
  const { data, isLoading, error } = useCompletionsQuery(query);

  // Create a simple graph configuration based on the graph type or use custom graph
  const graph: Graph = useMemo(() => {
    if (customGraph) return customGraph;
    switch (graphType) {
      case "bar":
        return {
          type: "bar",
          x: { field: "x", label: "Category" },
          y: [{ field: "y", label: "Count" }],
          stacked: false,
        };
      case "line":
        return {
          type: "line",
          x: { field: "x", label: "Time" },
          y: [{ field: "y", label: "Value" }],
        };
      case "pie":
        return {
          type: "pie",
          x: { field: "x", label: "Category" },
          y: [{ field: "y", label: "Count" }],
        };
      case "scatter":
        return {
          type: "scatter",
          x: { field: "x", label: "X Value" },
          y: [{ field: "y", label: "Y Value" }],
        };
      default:
        return {
          type: "bar",
          x: { field: "x", label: "Category" },
          y: [{ field: "y", label: "Count" }],
          stacked: false,
        };
    }
  }, [graphType, customGraph]);

  return (
    <div className="bg-white border border-gray-200 rounded-[2px] flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
        <p className="text-sm text-gray-600">{subtitle}</p>
      </div>

      {/* Graph Content */}
      <div className="flex-1">
        <CompletionsGraph
          data={data ?? []}
          isLoading={isLoading}
          error={error ? { error: error.message } : null}
          graph={graph}
          title={title}
          showBorder={false}
        />
      </div>
    </div>
  );
}
