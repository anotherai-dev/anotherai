import { memo } from "react";
import { MetricItem } from "./MetricItem";

type MetricsDisplayProps = {
  metrics?: { key: string; average: number }[];
  allMetricsPerKey?: Record<string, number[]>;
  versionMetricsPerKey?: Record<string, number[]>;
  showAvgPrefix?: boolean;
  className?: string; // Allow custom styling
  usePer1kMultiplier?: boolean; // Whether to use 1000 multiplier for costs
};

function MetricsDisplay(props: MetricsDisplayProps) {
  const {
    metrics,
    allMetricsPerKey,
    versionMetricsPerKey,
    showAvgPrefix = false,
    className = "space-y-1",
    usePer1kMultiplier = true,
  } = props;

  if (!metrics || metrics.length === 0) {
    return null;
  }

  return (
    <div className={className}>
      {metrics.map(({ key, average }) => (
        <MetricItem
          key={key}
          metricKey={key}
          average={average}
          allMetricsPerKey={allMetricsPerKey}
          versionMetricsPerKey={versionMetricsPerKey}
          showAvgPrefix={showAvgPrefix}
          usePer1kMultiplier={usePer1kMultiplier}
        />
      ))}
    </div>
  );
}

// Helper function to compare metrics arrays
function areMetricsEqual(
  prev?: { key: string; average: number }[],
  next?: { key: string; average: number }[]
): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i].key !== next[i].key || prev[i].average !== next[i].average) {
      return false;
    }
  }
  return true;
}

// Helper function to compare metrics per key objects
function areMetricsPerKeyEqual(prev?: Record<string, number[]>, next?: Record<string, number[]>): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;

  const prevKeys = Object.keys(prev);
  const nextKeys = Object.keys(next);

  if (prevKeys.length !== nextKeys.length) return false;

  for (const key of prevKeys) {
    const prevArray = prev[key];
    const nextArray = next[key];

    if (!nextArray || prevArray.length !== nextArray.length) return false;

    for (let i = 0; i < prevArray.length; i++) {
      if (prevArray[i] !== nextArray[i]) return false;
    }
  }

  return true;
}

export default memo(MetricsDisplay, (prevProps, nextProps) => {
  return (
    prevProps.showAvgPrefix === nextProps.showAvgPrefix &&
    prevProps.className === nextProps.className &&
    prevProps.usePer1kMultiplier === nextProps.usePer1kMultiplier &&
    areMetricsEqual(prevProps.metrics, nextProps.metrics) &&
    areMetricsPerKeyEqual(prevProps.allMetricsPerKey, nextProps.allMetricsPerKey) &&
    areMetricsPerKeyEqual(prevProps.versionMetricsPerKey, nextProps.versionMetricsPerKey)
  );
});
