import { cx } from "class-variance-authority";
import { getMetricBadgeColor } from "@/components/utils/utils";

type VersionHeaderMetricsProps = {
  metrics?: { key: string; average: number }[];
  allMetricsPerKey?: Record<string, number[]>; // All values for each metric key across versions for comparison
  showAvgPrefix?: boolean;
};

export function VersionHeaderMetrics(props: VersionHeaderMetricsProps) {
  const { metrics, allMetricsPerKey, showAvgPrefix } = props;

  if (!metrics || metrics.length === 0) {
    return null;
  }

  return (
    <div className="space-y-1 mt-1">
      {metrics.map(({ key, average }) => {
        // Use comparison coloring if all values are provided, otherwise use neutral styling
        const badgeColor =
          allMetricsPerKey && allMetricsPerKey[key]
            ? getMetricBadgeColor(average, allMetricsPerKey[key], true) // true = higher is better for most metrics
            : "bg-transparent border border-gray-200 text-gray-700";

        return (
          <div key={key} className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", badgeColor)}>
            <span className="text-gray-600 capitalize">
              {showAvgPrefix ? `Average ${key.replace(/_/g, " ")}` : key.replace(/_/g, " ")}
            </span>
            <span className="font-medium">{average.toFixed(2)}</span>
          </div>
        );
      })}
    </div>
  );
}
