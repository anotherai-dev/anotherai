import { Flowchart16Regular } from "@fluentui/react-icons";
import { useMemo } from "react";
import { formatCurrency } from "@/components/utils/utils";
import { TraceModelEntry } from "./TraceModelEntry";

type TraceAgentEntryProps = {
  agentId: string;
  models: Record<string, Record<string, unknown>[]>;
  currentCompletionId?: string;
  onNavigateToCompletion: (completionId: string) => void;
};

export function TraceAgentEntry(props: TraceAgentEntryProps) {
  const { agentId, models, currentCompletionId, onNavigateToCompletion } = props;

  // Calculate total cost and duration for all completions in this agent
  const totals = useMemo(() => {
    return Object.values(models)
      .flat()
      .reduce(
        (acc: { totalCost: number; totalDuration: number }, completion) => {
          const costMillionthUsd = completion.cost_millionth_usd as number | undefined;
          const durationDs = completion.duration_ds as number | undefined;

          if (costMillionthUsd) acc.totalCost += costMillionthUsd;
          if (durationDs) acc.totalDuration += durationDs;

          return acc;
        },
        { totalCost: 0, totalDuration: 0 }
      );
  }, [models]);

  const formatCost = (costMillionthUsd: number) => {
    const costUsd = costMillionthUsd / 1000000;
    return formatCurrency(costUsd, 1000);
  };

  const formatDuration = (durationDs: number) => {
    const durationS = durationDs / 10;
    return `${durationS.toFixed(2)}s`;
  };

  return (
    <div className="mb-4">
      <div className="text-gray-900 font-semibold text-[13px] flex items-center gap-1">
        <Flowchart16Regular className="text-gray-900" />
        <span>{agentId}</span>
      </div>
      <div className="text-gray-500 font-medium text-[12px] space-x-2 mb-2">
        <span>{formatCost(totals.totalCost)} (Per 1k completions)</span>
        <span>{formatDuration(totals.totalDuration)}</span>
      </div>
      {Object.entries(models).map(([modelId, completions]) => (
        <TraceModelEntry
          key={modelId}
          modelId={modelId}
          completions={completions}
          currentCompletionId={currentCompletionId}
          onNavigateToCompletion={onNavigateToCompletion}
        />
      ))}
    </div>
  );
}
