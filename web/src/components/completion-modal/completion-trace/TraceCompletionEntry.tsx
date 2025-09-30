import { ArrowSwap16Regular } from "@fluentui/react-icons";
import { formatCurrency } from "@/components/utils/utils";

type TraceCompletionEntryProps = {
  completion: Record<string, unknown>;
  index: number;
  currentCompletionId?: string;
  onNavigateToCompletion: (completionId: string) => void;
};

export function TraceCompletionEntry(props: TraceCompletionEntryProps) {
  const { completion, index, currentCompletionId, onNavigateToCompletion } = props;

  const costMillionthUsd = completion.cost_millionth_usd as number | undefined;
  const durationDs = completion.duration_ds as number | undefined;

  const formatCost = (costMillionthUsd: number | undefined) => {
    if (costMillionthUsd === undefined || costMillionthUsd === null) return "N/A";
    const costUsd = costMillionthUsd / 1000000;
    return formatCurrency(costUsd, 1000);
  };

  const formatDuration = (durationDs: number | undefined) => {
    if (durationDs === undefined || durationDs === null) return "N/A";
    const durationS = durationDs / 10;
    return `${durationS.toFixed(2)}s`;
  };

  const completionId = completion.id as string;
  const isSelected = currentCompletionId === completionId;

  const handleClick = () => {
    onNavigateToCompletion(completionId);
  };

  return (
    <div
      className={`mb-0.5 text-xs px-2 py-1.5 rounded-[2px] cursor-pointer transition-colors ${
        isSelected ? "bg-gray-100 border border-gray-300" : "hover:bg-gray-100 border border-transparent"
      }`}
      onClick={handleClick}
    >
      <div className="text-gray-900 font-semibold text-[13px] flex items-center gap-1">
        <ArrowSwap16Regular className="text-gray-800" />
        <span>Completion #{index}</span>
      </div>
      <div className="text-gray-500 font-medium text-[12px] space-x-2">
        <span>
          {formatCost(costMillionthUsd)}{" "}
          {costMillionthUsd !== undefined && costMillionthUsd !== null ? "(Per 1k completions)" : ""}
        </span>
        <span>{formatDuration(durationDs)}</span>
      </div>
    </div>
  );
}
