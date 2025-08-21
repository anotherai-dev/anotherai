import { cx } from "class-variance-authority";
import { useMemo, useState } from "react";
import { formatCurrency, formatDuration, getMetricBadgeColor } from "@/components/utils/utils";
import { HoverPopover } from "./HoverPopover";

type PriceAndLatencyDisplayProps = {
  cost: number;
  duration: number;
  // Optional props for comparison coloring (used in version headers)
  allCosts?: number[];
  allDurations?: number[];
  // Version-specific arrays for percentiles
  versionCosts?: number[];
  versionDurations?: number[];
  showAvgPrefix?: boolean;
};

// Percentiles Popover Component
function PercentilesPopover({
  p50,
  p90,
  p99,
  formatValue,
}: {
  p50: number;
  p90: number;
  p99: number;
  formatValue: (val: number) => string;
}) {
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

export function PriceAndLatencyDisplay(props: PriceAndLatencyDisplayProps) {
  const { cost, duration, allCosts, allDurations, versionCosts, versionDurations, showAvgPrefix } = props;

  const costBadgeColor = getMetricBadgeColor(cost, allCosts || []);
  const durationBadgeColor = getMetricBadgeColor(duration, allDurations || []);

  // Calculate percentiles from version-specific data
  const costPercentiles = useMemo(() => {
    if (!versionCosts || versionCosts.length === 0) return null;

    const sorted = [...versionCosts].sort((a, b) => a - b);
    const p50Index = Math.floor(sorted.length * 0.5);
    const p90Index = Math.floor(sorted.length * 0.9);
    const p99Index = Math.floor(sorted.length * 0.99);

    return {
      p50: sorted[p50Index],
      p90: sorted[p90Index],
      p99: sorted[p99Index],
    };
  }, [versionCosts]);

  const durationPercentiles = useMemo(() => {
    if (!versionDurations || versionDurations.length === 0) return null;

    const sorted = [...versionDurations].sort((a, b) => a - b);
    const p50Index = Math.floor(sorted.length * 0.5);
    const p90Index = Math.floor(sorted.length * 0.9);
    const p99Index = Math.floor(sorted.length * 0.99);

    return {
      p50: sorted[p50Index],
      p90: sorted[p90Index],
      p99: sorted[p99Index],
    };
  }, [versionDurations]);

  return (
    <div className="space-y-1">
      <div className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", costBadgeColor)}>
        <span className="text-gray-600">{showAvgPrefix ? "Average Cost (per 1K)" : "Cost (per 1K)"}</span>
        {showAvgPrefix && costPercentiles ? (
          <HoverPopover
            content={<PercentilesPopover {...costPercentiles} formatValue={formatCurrency} />}
            position="topRightAligned"
          >
            <span className="font-medium cursor-pointer">{formatCurrency(cost)}</span>
          </HoverPopover>
        ) : (
          <span className="font-medium">{formatCurrency(cost)}</span>
        )}
      </div>
      <div className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", durationBadgeColor)}>
        <span className="text-gray-600">{showAvgPrefix ? "Average Duration" : "Duration"}</span>
        {showAvgPrefix && durationPercentiles ? (
          <HoverPopover
            content={<PercentilesPopover {...durationPercentiles} formatValue={formatDuration} />}
            position="topRightAligned"
          >
            <span className="font-medium cursor-pointer">{formatDuration(duration)}</span>
          </HoverPopover>
        ) : (
          <span className="font-medium">{formatDuration(duration)}</span>
        )}
      </div>
    </div>
  );
}
