import { useMemo } from "react";
import { formatNumber } from "@/components/universal-charts/utils";
import { Trace } from "@/types/models";
import InfoRow from "./InfoRow";

type Props = {
  traces?: Trace[];
};

export function TracesView({ traces }: Props) {
  const llmTracesWithUsage = useMemo(() => {
    if (!traces || traces.length === 0) {
      return [];
    }

    // Filter for LLM traces that have usage data with text_token_count
    return traces.filter((trace): trace is Extract<Trace, { kind: "llm" }> => {
      if (trace.kind !== "llm" || !trace.usage) return false;

      // Check if any usage entry has text_token_count
      return Object.values(trace.usage).some(
        (usageValue: unknown) =>
          typeof usageValue === "object" && usageValue !== null && "text_token_count" in usageValue
      );
    });
  }, [traces]);

  if (llmTracesWithUsage.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-gray-200 border-dashed pt-3 px-4 mt-3">
      <div className="w-full space-y-2 py-1">
        <div className="text-xs font-medium text-gray-400 mb-2">Traces</div>
        {llmTracesWithUsage.map((trace, traceIndex) => (
          <div key={traceIndex} className="space-y-2">
            {/* Show provider if available */}
            {trace.provider && <InfoRow key={`${traceIndex}-provider`} title="Provider" value={trace.provider} />}
            {trace.usage &&
              Object.entries(trace.usage).map(([key, usageValue]) => {
                // Type guard to check if usageValue has the expected properties
                if (typeof usageValue !== "object" || usageValue === null || !("text_token_count" in usageValue)) {
                  return null;
                }

                const usageData = usageValue as {
                  text_token_count: number;
                  cost_usd?: number;
                };

                const textTokenCount = usageData.text_token_count;
                const costUsd = usageData.cost_usd;

                if (textTokenCount === undefined) return null;

                // Format the title based on the key
                const formatTitle = (key: string) => {
                  const capitalizedKey = key.charAt(0).toUpperCase() + key.slice(1);
                  return `${capitalizedKey} Token Count`;
                };

                const formatCostTitle = (key: string) => {
                  const capitalizedKey = key.charAt(0).toUpperCase() + key.slice(1);
                  return `${capitalizedKey} Cost`;
                };

                return (
                  <div key={`${traceIndex}-${key}`} className="space-y-2">
                    <InfoRow title={formatTitle(key)} value={`${textTokenCount.toLocaleString()}`} />
                    {costUsd !== undefined && (
                      <InfoRow title={formatCostTitle(key)} value={`$${formatNumber(costUsd)}`} />
                    )}
                  </div>
                );
              })}
          </div>
        ))}
      </div>
    </div>
  );
}
