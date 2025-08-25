import { TraceCompletionEntry } from "./TraceCompletionEntry";

type TraceModelEntryProps = {
  modelId: string;
  completions: Record<string, unknown>[];
  currentCompletionId?: string;
  onNavigateToCompletion: (completionId: string) => void;
};

export function TraceModelEntry(props: TraceModelEntryProps) {
  const { modelId, completions, currentCompletionId, onNavigateToCompletion } = props;

  return (
    <div className="ml-4 mb-2">
      <div className="text-xs text-gray-600 mb-1">{modelId}</div>
      <div className="ml-4">
        {completions.map((completion, index) => (
          <TraceCompletionEntry
            key={completion.id as string}
            completion={completion}
            index={index + 1}
            currentCompletionId={currentCompletionId}
            onNavigateToCompletion={onNavigateToCompletion}
          />
        ))}
      </div>
    </div>
  );
}
