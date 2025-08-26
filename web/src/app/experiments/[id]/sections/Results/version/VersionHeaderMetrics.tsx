import { cx } from "class-variance-authority";
import { ArrowUp } from "lucide-react";
import { getMetricBadgeWithRelative } from "@/components/utils/utils";

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
        const badgeInfo =
          allMetricsPerKey && allMetricsPerKey[key]
            ? getMetricBadgeWithRelative(average, allMetricsPerKey[key], true) // true = higher is better for most metrics
            : {
                color: "bg-transparent border border-gray-200 text-gray-700",
                relativeText: undefined,
                isBest: false,
                isWorst: false,
              };

        return (
          <div key={key} className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", badgeInfo.color)}>
            <span className="text-gray-600 capitalize">
              {showAvgPrefix ? `Average ${key.replace(/_/g, " ")}` : key.replace(/_/g, " ")}
            </span>
            <div className="flex items-center gap-1">
              {badgeInfo.relativeText && badgeInfo.isBest && (
                <span className="text-xs text-gray-500">{badgeInfo.relativeText}</span>
              )}
              {badgeInfo.relativeText && !badgeInfo.isBest && (
                <span className="flex items-center text-xs font-medium text-red-500">
                  {badgeInfo.relativeText}
                  <ArrowUp size={12} />
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
