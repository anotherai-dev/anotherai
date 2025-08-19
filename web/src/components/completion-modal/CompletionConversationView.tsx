import { useMemo } from "react";
import { findAllMetricKeysAndAverages } from "@/app/experiments/[id]/utils";
import { Annotation, Completion, Message } from "@/types/models";
import { PageError } from "../PageError";
import { MessagesViewer } from "../messages/MessagesViewer";

type Props = {
  completion: Completion;
  annotations?: Annotation[];
  onKeypathSelect?: (keyPath: string) => void;
};

export function CompletionConversationView(props: Props) {
  const { completion, annotations, onKeypathSelect } = props;

  const messages = useMemo(() => {
    const allMessages: Message[] = [];

    // Add messages from completion.messages first
    if (completion.messages) {
      allMessages.push(...completion.messages);
    }

    // Add messages from output.messages next
    if (completion.output?.messages) {
      const outputMessages = [...completion.output.messages];

      // Get metrics for this completion
      const completionMetrics = annotations
        ? findAllMetricKeysAndAverages(
            annotations.filter((annotation) => annotation.target?.completion_id === completion.id && annotation.metric)
          )
        : [];

      // Add cost, duration, reasoning tokens, and metrics to the last output message
      if (outputMessages.length > 0) {
        const lastIndex = outputMessages.length - 1;
        outputMessages[lastIndex] = {
          ...outputMessages[lastIndex],
          cost_usd: completion.cost_usd,
          duration_seconds: completion.duration_seconds,
          reasoning_token_count: completion.reasoning_token_count,
          metrics: completionMetrics,
        };
      }

      allMessages.push(...outputMessages);
    }

    return allMessages;
  }, [
    completion.messages,
    completion.output?.messages,
    completion.cost_usd,
    completion.duration_seconds,
    completion.reasoning_token_count,
    annotations,
    completion.id,
  ]);

  return (
    <div className="flex flex-col w-full h-full">
      <div className="text-base font-bold py-3 px-4 border-b border-gray-200 border-dashed text-gray-600">
        Conversation
      </div>

      <div className="px-4 pt-4 overflow-y-auto space-y-3">
        <MessagesViewer messages={messages} annotations={annotations} onKeypathSelect={onKeypathSelect} />

        {completion.output?.error && <PageError error={completion.output.error} />}
      </div>
    </div>
  );
}
