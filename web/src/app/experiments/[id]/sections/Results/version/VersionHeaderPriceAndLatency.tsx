import { PriceAndLatencyDisplay } from "@/components/PriceAndLatencyDisplay";

type VersionHeaderPriceAndLatencyProps = {
  priceAndLatency?: {
    avgCost: number;
    avgDuration: number;
    allCosts: number[];
    allDurations: number[];
    versionCosts: number[];
    versionDurations: number[];
  };
  showAvgPrefix?: boolean;
};

export function VersionHeaderPriceAndLatency(props: VersionHeaderPriceAndLatencyProps) {
  const { priceAndLatency, showAvgPrefix } = props;

  if (!priceAndLatency) {
    return null;
  }

  return (
    <PriceAndLatencyDisplay
      cost={priceAndLatency.avgCost}
      duration={priceAndLatency.avgDuration}
      allCosts={priceAndLatency.allCosts}
      allDurations={priceAndLatency.allDurations}
      versionCosts={priceAndLatency.versionCosts}
      versionDurations={priceAndLatency.versionDurations}
      showAvgPrefix={showAvgPrefix}
    />
  );
}
