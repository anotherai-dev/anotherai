import { useMemo } from "react";
import { formatCurrency, formatDuration } from "@/components/utils/utils";
import { Message } from "@/types/models";

type MessageMetricsDisplayProps = {
  message: Message;
};

export function MessageMetricsDisplay({ message }: MessageMetricsDisplayProps) {
  const allMetrics = useMemo(() => {
    const combinedMetrics: Array<{ key: string; average: number }> = [];

    // Add cost and duration if available
    if (message.cost_usd) {
      combinedMetrics.push({ key: "cost", average: message.cost_usd });
    }
    if (message.duration_seconds) {
      combinedMetrics.push({ key: "duration", average: message.duration_seconds });
    }

    // Add other metrics
    if (message.metrics && message.metrics.length > 0) {
      combinedMetrics.push(...message.metrics);
    }

    return combinedMetrics;
  }, [message.cost_usd, message.duration_seconds, message.metrics]);

  if (allMetrics.length === 0) return null;

  return (
    <div className="border-t border-gray-200">
      <div className="grid grid-cols-2 gap-0">
        {allMetrics.map((metric, index) => {
          const isEven = index % 2 === 0;
          const isLastOdd = index === allMetrics.length - 1 && allMetrics.length % 2 === 1;

          // Calculate which row this item is in (0-based)
          const currentRow = Math.floor(index / 2);
          const totalRows = Math.ceil(allMetrics.length / 2);
          const isInLastRow = currentRow === totalRows - 1;

          let formattedValue = metric.average.toFixed(2);
          if (metric.key === "cost") {
            formattedValue = formatCurrency(metric.average, 1000);
          } else if (metric.key === "duration") {
            formattedValue = formatDuration(metric.average);
          }

          return (
            <div
              key={metric.key}
              className={`px-3 py-3 text-xs bg-gray-50 flex justify-between items-center ${
                !isEven ? "border-l border-gray-200" : ""
              } ${isLastOdd ? "col-span-2" : ""} ${!isInLastRow ? "border-b border-gray-200" : ""}`}
            >
              <span className="font-medium text-gray-600 capitalize">
                {metric.key === "cost" ? "cost (Per 1k completions)" : metric.key.replace(/_/g, " ")}
              </span>
              <span className="text-gray-800">{formattedValue}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
