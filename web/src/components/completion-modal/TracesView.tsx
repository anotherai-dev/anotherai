import { useMemo } from "react";
import { formatNumber } from "@/components/universal-charts/utils";
import { Trace } from "@/types/models";
import InfoRow from "./InfoRow";

type Props = {
  traces?: Trace[];
};

type UsageInfoProps = {
  trace: Extract<Trace, { kind: "llm" }>;
  traceIndex: number;
};

function UsageInfo({ trace, traceIndex }: UsageInfoProps) {
  if (!trace.usage) return null;

  // Check if this is the new detailed usage structure
  if ("prompt" in trace.usage && "completion" in trace.usage) {
    const detailedUsage = trace.usage as {
      prompt: { text_token_count?: number; cost_usd: number };
      completion: { text_token_count?: number; reasoning_token_count?: number; cached_token_count?: number; cost_usd: number };
    };

    const items = [];

    // Prompt tokens
    if (detailedUsage.prompt.text_token_count) {
      items.push(
        <InfoRow
          key={`${traceIndex}-prompt-tokens`}
          title="Prompt Tokens"
          value={detailedUsage.prompt.text_token_count.toLocaleString()}
        />
      );
    }

    // Completion tokens
    if (detailedUsage.completion.text_token_count) {
      items.push(
        <InfoRow
          key={`${traceIndex}-completion-tokens`}
          title="Completion Tokens"
          value={detailedUsage.completion.text_token_count.toLocaleString()}
        />
      );
    }

    // Reasoning tokens (new!)
    if (detailedUsage.completion.reasoning_token_count && detailedUsage.completion.reasoning_token_count > 0) {
      items.push(
        <InfoRow
          key={`${traceIndex}-reasoning-tokens`}
          title="Reasoning Tokens"
          value={detailedUsage.completion.reasoning_token_count.toLocaleString()}
        />
      );
    }

    // Cached tokens
    if (detailedUsage.completion.cached_token_count && detailedUsage.completion.cached_token_count > 0) {
      items.push(
        <InfoRow
          key={`${traceIndex}-cached-tokens`}
          title="Cached Tokens"
          value={detailedUsage.completion.cached_token_count.toLocaleString()}
        />
      );
    }

    // Total cost
    const totalCost = detailedUsage.prompt.cost_usd + detailedUsage.completion.cost_usd;
    if (totalCost > 0) {
      items.push(
        <InfoRow
          key={`${traceIndex}-total-cost`}
          title="Total Cost"
          value={`$${formatNumber(totalCost)}`}
        />
      );
    }

    return <>{items}</>;
  }

  // Fallback to old simple structure
  const simpleUsage = trace.usage as { input_tokens?: number; output_tokens?: number; total_tokens?: number };
  const items = [];

  if (simpleUsage.input_tokens) {
    items.push(
      <InfoRow
        key={`${traceIndex}-input-tokens`}
        title="Input Tokens"
        value={simpleUsage.input_tokens.toLocaleString()}
      />
    );
  }

  if (simpleUsage.output_tokens) {
    items.push(
      <InfoRow
        key={`${traceIndex}-output-tokens`}
        title="Output Tokens"
        value={simpleUsage.output_tokens.toLocaleString()}
      />
    );
  }

  if (simpleUsage.total_tokens) {
    items.push(
      <InfoRow
        key={`${traceIndex}-total-tokens`}
        title="Total Tokens"
        value={simpleUsage.total_tokens.toLocaleString()}
      />
    );
  }

  return <>{items}</>;
}

export function TracesView({ traces }: Props) {
  const llmTracesWithUsage = useMemo(() => {
    if (!traces || traces.length === 0) {
      return [];
    }

    // Filter for LLM traces that have usage data
    return traces.filter((trace): trace is Extract<Trace, { kind: "llm" }> => {
      if (trace.kind !== "llm" || !trace.usage) return false;

      // Check if usage has the new detailed structure or old simple structure
      const hasDetailedUsage = "prompt" in trace.usage && "completion" in trace.usage;
      const hasSimpleUsage = "input_tokens" in trace.usage || "output_tokens" in trace.usage;

      return hasDetailedUsage || hasSimpleUsage;
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
            <UsageInfo trace={trace} traceIndex={traceIndex} />
          </div>
        ))}
      </div>
    </div>
  );
}
