import { cx } from "class-variance-authority";
import { ArrowUp } from "lucide-react";
import { getMetricBadgeWithRelative } from "@/components/utils/utils";

type CompletionMetricsProps = {
  metrics?: { key: string; average: number }[];
  allMetricsPerKeyForRow?: Record<string, number[]>; // All metric values for this row (input) across versions
};

export function CompletionMetrics(props: CompletionMetricsProps) {
  const { metrics, allMetricsPerKeyForRow } = props;

  if (!metrics || metrics.length === 0) {
    return null;
  }

  return (
    <div className="space-y-1">
      {metrics.map(({ key, average }) => {
        // Determine metric type and comparison logic
        const metricType = key.includes("cost")
          ? "cost"
          : key.includes("duration") || key.includes("latency")
            ? "duration"
            : undefined;
        const isHigherBetter = !metricType; // For cost/duration, lower is better; for other metrics, higher is better

        // Use row-based comparison coloring if available
        const badgeInfo =
          allMetricsPerKeyForRow && allMetricsPerKeyForRow[key]
            ? getMetricBadgeWithRelative(average, allMetricsPerKeyForRow[key], isHigherBetter, metricType)
            : {
                color: "bg-transparent border border-gray-200 text-gray-700",
                relativeText: undefined,
                isBest: false,
                isWorst: false,
              };

        return (
          <div key={key} className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", badgeInfo.color)}>
            <span className="text-gray-600 capitalize">{key.replace(/_/g, " ")}</span>
            <div className="flex items-center gap-1">
              {badgeInfo.relativeText && badgeInfo.isBest && (
                <span className="text-xs text-gray-500">{badgeInfo.relativeText}</span>
              )}
              {badgeInfo.relativeText && !badgeInfo.isBest && (
                <span className="flex items-center text-xs font-medium text-red-500">
                  {badgeInfo.relativeText}
                  {badgeInfo.showArrow && <ArrowUp size={12} />}
                </span>
              )}
              <span className="font-medium">{average.toFixed(2)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
