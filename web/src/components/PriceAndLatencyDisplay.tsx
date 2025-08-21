import { cx } from "class-variance-authority";
import { ArrowUp } from "lucide-react";
import { formatCurrency, formatDuration, getMetricBadgeWithRelative } from "@/components/utils/utils";
import { HoverPopover } from "./HoverPopover";

type PriceAndLatencyDisplayProps = {
  cost: number;
  duration: number;
  // Optional props for comparison coloring (used in version headers)
  allCosts?: number[];
  allDurations?: number[];
  // Optional props for version-specific percentiles (used for popover data)
  versionCosts?: number[];
  versionDurations?: number[];
  showAvgPrefix?: boolean;
};

type PercentilesPopoverProps = {
  p50: number;
  p90: number;
  p99: number;
  formatValue: (value: number) => string;
};

function PercentilesPopover({ p50, p90, p99, formatValue }: PercentilesPopoverProps) {
  return (
    <div className="space-y-1 py-1 w-[120px]">
      <div className="flex justify-between items-center">
        <span>p50:</span>
        <span className="font-medium bg-white/10 px-2 py-1 rounded-[2px] border border-white/10">
          {formatValue(p50)}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span>p90:</span>
        <span className="font-medium bg-white/10 px-2 py-1 rounded-[2px] border border-white/10">
          {formatValue(p90)}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span>p99:</span>
        <span className="font-medium bg-white/10 px-2 py-1 rounded-[2px] border border-white/10">
          {formatValue(p99)}
        </span>
      </div>
    </div>
  );
}

function calculatePercentile(sortedArray: number[], percentile: number): number {
  const index = (percentile / 100) * (sortedArray.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index % 1;

  if (upper >= sortedArray.length) return sortedArray[sortedArray.length - 1];
  return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
}

export function PriceAndLatencyDisplay(props: PriceAndLatencyDisplayProps) {
  const { cost, duration, allCosts, allDurations, versionCosts, versionDurations, showAvgPrefix } = props;

  // Use comparison coloring if arrays are provided, otherwise use neutral styling
  const costBadgeInfo = allCosts
    ? getMetricBadgeWithRelative(cost, allCosts, false)
    : {
        color: "bg-transparent border border-gray-200 text-gray-700",
        relativeText: undefined,
        isBest: false,
        isWorst: false,
      };

  const durationBadgeInfo = allDurations
    ? getMetricBadgeWithRelative(duration, allDurations, false)
    : {
        color: "bg-transparent border border-gray-200 text-gray-700",
        relativeText: undefined,
        isBest: false,
        isWorst: false,
      };

  // Calculate percentiles for duration using version-specific data if available
  const durationPercentiles =
    versionDurations && versionDurations.length > 0
      ? (() => {
          const sorted = [...versionDurations].sort((a, b) => a - b);
          return {
            p50: calculatePercentile(sorted, 50),
            p90: calculatePercentile(sorted, 90),
            p99: calculatePercentile(sorted, 99),
          };
        })()
      : null;

  // Calculate percentiles for cost using version-specific data if available
  const costPercentiles =
    versionCosts && versionCosts.length > 0
      ? (() => {
          const sorted = [...versionCosts].sort((a, b) => a - b);
          return {
            p50: calculatePercentile(sorted, 50),
            p90: calculatePercentile(sorted, 90),
            p99: calculatePercentile(sorted, 99),
          };
        })()
      : null;

  return (
    <div className="space-y-1">
      {costPercentiles && showAvgPrefix ? (
        <HoverPopover
          content={
            <PercentilesPopover
              p50={costPercentiles.p50}
              p90={costPercentiles.p90}
              p99={costPercentiles.p99}
              formatValue={formatCurrency}
            />
          }
          position="topRightAlignedNew"
          popoverClassName="bg-gray-800 text-white rounded-[4px]"
          className=""
        >
          <div
            className={cx(
              "flex justify-between items-center px-2 py-1 rounded text-xs cursor-pointer",
              costBadgeInfo.color
            )}
          >
            <span className="text-gray-600">{showAvgPrefix ? "Average Cost (per 1K)" : "Cost (per 1K)"}</span>
            <div className="flex items-center gap-1">
              {costBadgeInfo.relativeText && costBadgeInfo.isBest && (
                <span className="text-xs text-gray-500">{costBadgeInfo.relativeText}</span>
              )}
              {costBadgeInfo.relativeText && !costBadgeInfo.isBest && (
                <span className="flex items-center text-xs font-medium text-red-500">
                  {costBadgeInfo.relativeText}
                  <ArrowUp size={12} />
                </span>
              )}
              <span className="font-medium">{formatCurrency(cost)}</span>
            </div>
          </div>
        </HoverPopover>
      ) : (
        <div className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", costBadgeInfo.color)}>
          <span className="text-gray-600">{showAvgPrefix ? "Average Cost (per 1K)" : "Cost (per 1K)"}</span>
          <div className="flex items-center gap-1">
            {costBadgeInfo.relativeText && costBadgeInfo.isBest && (
              <span className="text-xs text-gray-500">{costBadgeInfo.relativeText}</span>
            )}
            {costBadgeInfo.relativeText && !costBadgeInfo.isBest && (
              <span className="flex items-center text-xs font-medium text-red-500">
                {costBadgeInfo.relativeText}
                <ArrowUp size={12} />
              </span>
            )}
            <span className="font-medium">{formatCurrency(cost)}</span>
          </div>
        </div>
      )}
      {durationPercentiles && showAvgPrefix ? (
        <HoverPopover
          content={
            <PercentilesPopover
              p50={durationPercentiles.p50}
              p90={durationPercentiles.p90}
              p99={durationPercentiles.p99}
              formatValue={formatDuration}
            />
          }
          position="topRightAlignedNew"
          popoverClassName="bg-gray-800 text-white rounded-[4px]"
          className=""
        >
          <div
            className={cx(
              "flex justify-between items-center px-2 py-1 rounded text-xs cursor-pointer",
              durationBadgeInfo.color
            )}
          >
            <span className="text-gray-600">{showAvgPrefix ? "Average Duration" : "Duration"}</span>
            <div className="flex items-center gap-1">
              {durationBadgeInfo.relativeText && durationBadgeInfo.isBest && (
                <span className="text-xs text-gray-500">{durationBadgeInfo.relativeText}</span>
              )}
              {durationBadgeInfo.relativeText && !durationBadgeInfo.isBest && (
                <span className="flex items-center text-xs font-medium text-red-500">
                  {durationBadgeInfo.relativeText}
                  <ArrowUp size={12} />
                </span>
              )}
              <span className="font-medium">{formatDuration(duration)}</span>
            </div>
          </div>
        </HoverPopover>
      ) : (
        <div className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", durationBadgeInfo.color)}>
          <span className="text-gray-600">{showAvgPrefix ? "Average Duration" : "Duration"}</span>
          <div className="flex items-center gap-1">
            {durationBadgeInfo.relativeText && durationBadgeInfo.isBest && (
              <span className="text-xs text-gray-500">{durationBadgeInfo.relativeText}</span>
            )}
            {durationBadgeInfo.relativeText && !durationBadgeInfo.isBest && (
              <span className="flex items-center text-xs font-medium text-red-500">
                {durationBadgeInfo.relativeText}
                <ArrowUp size={12} />
              </span>
            )}
            <span className="font-medium">{formatDuration(duration)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
