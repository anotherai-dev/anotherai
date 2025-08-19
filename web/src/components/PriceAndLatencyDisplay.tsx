import { cx } from "class-variance-authority";
import { formatCurrency, formatDuration, formatTokens, getMetricBadgeColor } from "@/components/utils/utils";

type PriceAndLatencyDisplayProps = {
  cost: number;
  duration: number;
  reasoningTokens?: number;
  // Optional props for comparison coloring (used in version headers)
  allCosts?: number[];
  allDurations?: number[];
  showAvgPrefix?: boolean;
};

export function PriceAndLatencyDisplay(props: PriceAndLatencyDisplayProps) {
  const { cost, duration, reasoningTokens, allCosts, allDurations, showAvgPrefix } = props;

  // Use comparison coloring if arrays are provided, otherwise use neutral styling
  const costBadgeColor = allCosts
    ? getMetricBadgeColor(cost, allCosts, false)
    : "bg-transparent border border-gray-200 text-gray-700";

  const durationBadgeColor = allDurations
    ? getMetricBadgeColor(duration, allDurations, false)
    : "bg-transparent border border-gray-200 text-gray-700";

  const hasReasoningTokens = reasoningTokens != null && reasoningTokens > 0;

  return (
    <div className="space-y-1">
      <div className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", costBadgeColor)}>
        <span className="text-gray-600">{showAvgPrefix ? "Average Cost" : "Cost"}</span>
        <span className="font-medium">{formatCurrency(cost)}</span>
      </div>
      <div className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", durationBadgeColor)}>
        <span className="text-gray-600">{showAvgPrefix ? "Average Duration" : "Duration"}</span>
        <span className="font-medium">{formatDuration(duration)}</span>
      </div>
      {hasReasoningTokens && (
        <div className="flex justify-between items-center px-2 py-1 rounded text-xs bg-transparent border border-gray-200 text-gray-700">
          <span className="text-gray-600">{showAvgPrefix ? "Average Reasoning" : "Reasoning"}</span>
          <span className="font-medium">{formatTokens(reasoningTokens)}</span>
        </div>
      )}
    </div>
  );
}
