import { TraceAgentEntry } from "./TraceAgentEntry";

type CompletionTraceViewProps = {
  groupedTraceCompletions: Record<string, Record<string, Record<string, unknown>[]>> | undefined;
  currentCompletionId?: string;
  onNavigateToCompletion: (completionId: string) => void;
};

export function CompletionTraceView(props: CompletionTraceViewProps) {
  const { groupedTraceCompletions, currentCompletionId, onNavigateToCompletion } = props;

  return (
    <div className="flex flex-col w-full h-full">
      <div className="text-base font-bold py-3 px-4 border-b border-gray-200 border-dashed text-gray-600">Trace</div>
      <div className="flex-1 w-full overflow-y-auto">
        {groupedTraceCompletions && Object.keys(groupedTraceCompletions).length > 0 ? (
          <div className="px-4 pt-4">
            {Object.entries(groupedTraceCompletions).map(([agentId, models]) => (
              <TraceAgentEntry
                key={agentId}
                agentId={agentId}
                models={models}
                currentCompletionId={currentCompletionId}
                onNavigateToCompletion={onNavigateToCompletion}
              />
            ))}
          </div>
        ) : (
          <div className="px-4 pt-4 text-gray-500 italic" style={{ fontSize: "13px" }}>
            No trace completions
          </div>
        )}
      </div>
    </div>
  );
}
