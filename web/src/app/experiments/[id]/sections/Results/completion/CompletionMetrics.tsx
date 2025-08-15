import { cx } from "class-variance-authority";
import { getMetricBadgeColor } from "@/components/utils/utils";

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
        // Use row-based comparison coloring if available
        const badgeColor =
          allMetricsPerKeyForRow && allMetricsPerKeyForRow[key]
            ? getMetricBadgeColor(average, allMetricsPerKeyForRow[key], true) // true = higher is better for most metrics
            : "bg-transparent border border-gray-200 text-gray-700";

        return (
          <div key={key} className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", badgeColor)}>
            <span className="text-gray-600 capitalize">{key.replace(/_/g, " ")}</span>
            <span className="font-medium">{average.toFixed(2)}</span>
          </div>
        );
      })}
    </div>
  );
}
