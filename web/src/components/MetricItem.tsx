import { cx } from "class-variance-authority";
import { ArrowUp } from "lucide-react";
import { memo, useMemo } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { formatCurrency, formatDuration, getMetricBadgeWithRelative } from "@/components/utils/utils";

type MetricItemProps = {
  metricKey: string;
  average: number;
  allMetricsPerKey?: Record<string, number[]>;
  versionMetricsPerKey?: Record<string, number[]>; // Version-specific data for percentiles
  showAvgPrefix?: boolean;
};

type PercentilesPopoverProps = {
  p50: number;
  p90: number;
  p99: number;
  formatValue: (value: number) => string;
};

const PercentilesPopover = memo(function PercentilesPopover({ p50, p90, p99, formatValue }: PercentilesPopoverProps) {
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
});

function calculatePercentile(sortedArray: number[], percentile: number): number {
  const index = (percentile / 100) * (sortedArray.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  const weight = index % 1;

  if (upper >= sortedArray.length) return sortedArray[sortedArray.length - 1];
  return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
}

export function MetricItem({
  metricKey,
  average,
  allMetricsPerKey,
  versionMetricsPerKey,
  showAvgPrefix,
}: MetricItemProps) {
  const metricType = useMemo(() => {
    if (metricKey.includes("cost")) {
      return "cost";
    }
    if (metricKey.includes("duration") || metricKey.includes("latency")) {
      return "duration";
    }
    return undefined;
  }, [metricKey]);

  const isHigherBetter = !metricType;

  const badgeInfo = useMemo(() => {
    if (metricType === undefined || allMetricsPerKey === undefined || allMetricsPerKey[metricKey] === undefined) {
      return {
        color: "bg-transparent border border-gray-200 text-gray-700",
        relativeText: undefined,
        isBest: false,
        isWorst: false,
      };
    }

    return getMetricBadgeWithRelative(average, allMetricsPerKey[metricKey], isHigherBetter, metricType);
  }, [allMetricsPerKey, metricKey, average, isHigherBetter, metricType]);

  const percentiles = useMemo(() => {
    const versionData = versionMetricsPerKey?.[metricKey];
    if (!versionData || versionData.length === 0) {
      return null;
    }

    const sorted = [...versionData].sort((a, b) => a - b);
    return {
      p50: calculatePercentile(sorted, 50),
      p90: calculatePercentile(sorted, 90),
      p99: calculatePercentile(sorted, 99),
    };
  }, [versionMetricsPerKey, metricKey]);

  const formatValue = useMemo(() => {
    if (metricType === "cost") {
      return (value: number) => formatCurrency(value, 1000);
    } else if (metricType === "duration") {
      return formatDuration;
    } else {
      return (value: number) => value.toFixed(2);
    }
  }, [metricType]);

  const displayLabel = showAvgPrefix
    ? `Average ${metricKey === "cost" ? "cost (Per 1k completions)" : metricKey.replace(/_/g, " ")}`
    : metricKey === "cost"
      ? "cost (Per 1k completions)"
      : metricKey.replace(/_/g, " ");

  if (percentiles && showAvgPrefix) {
    return (
      <HoverPopover
        content={
          <PercentilesPopover
            p50={percentiles.p50}
            p90={percentiles.p90}
            p99={percentiles.p99}
            formatValue={formatValue}
          />
        }
        position="topRightAlignedNew"
        popoverClassName="bg-gray-800 text-white rounded-[4px]"
        className=""
      >
        <div
          className={cx("flex justify-between items-center px-2 py-1 rounded text-xs cursor-pointer", badgeInfo.color)}
        >
          <span className="text-gray-600 capitalize">{displayLabel}</span>
          <div className="flex items-center gap-1">
            {metricType && badgeInfo.relativeText && badgeInfo.isBest && (
              <span className="text-xs text-gray-500">{badgeInfo.relativeText}</span>
            )}
            {metricType && badgeInfo.relativeText && !badgeInfo.isBest && (
              <span className="flex items-center text-xs font-medium text-red-500">
                {badgeInfo.relativeText}
                {badgeInfo.showArrow && <ArrowUp size={12} />}
              </span>
            )}
            <span className="font-medium">{formatValue(average)}</span>
          </div>
        </div>
      </HoverPopover>
    );
  }

  return (
    <div className={cx("flex justify-between items-center px-2 py-1 rounded text-xs", badgeInfo.color)}>
      <span className="text-gray-600 capitalize">{displayLabel}</span>
      <div className="flex items-center gap-1">
        {metricType && badgeInfo.relativeText && badgeInfo.isBest && (
          <span className="text-xs text-gray-500">{badgeInfo.relativeText}</span>
        )}
        {metricType && badgeInfo.relativeText && !badgeInfo.isBest && (
          <span className="flex items-center text-xs font-medium text-red-500">
            {badgeInfo.relativeText}
            {badgeInfo.showArrow && <ArrowUp size={12} />}
          </span>
        )}
        <span className="font-medium">{formatValue(average)}</span>
      </div>
    </div>
  );
}
