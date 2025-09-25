import { memo } from "react";
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

function VersionHeaderPriceAndLatency(props: VersionHeaderPriceAndLatencyProps) {
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

// Helper function to compare priceAndLatency objects
function arePriceAndLatencyEqual(prev?: VersionHeaderPriceAndLatencyProps['priceAndLatency'], next?: VersionHeaderPriceAndLatencyProps['priceAndLatency']): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  
  return (
    prev.avgCost === next.avgCost &&
    prev.avgDuration === next.avgDuration &&
    prev.allCosts === next.allCosts &&
    prev.allDurations === next.allDurations &&
    prev.versionCosts === next.versionCosts &&
    prev.versionDurations === next.versionDurations
  );
}

export default memo(VersionHeaderPriceAndLatency, (prevProps, nextProps) => {
  return (
    prevProps.showAvgPrefix === nextProps.showAvgPrefix &&
    arePriceAndLatencyEqual(prevProps.priceAndLatency, nextProps.priceAndLatency)
  );
});
