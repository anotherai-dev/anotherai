import { Copy } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { memo, useMemo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import MetricsDisplay from "@/components/MetricsDisplay";
import { PageError } from "@/components/PageError";
import { useToast } from "@/components/ToastProvider";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { shouldIncludeCostMetric, shouldIncludeDurationMetric } from "@/components/utils/utils";
import { Annotation, ExperimentCompletion } from "@/types/models";
import { getMetricsForCompletion } from "../../../utils";

export type CompletionCellProps = {
  completion: ExperimentCompletion | undefined;
  annotations?: Annotation[]; // All annotations from experiment
  experimentId?: string;
  allMetricsPerKey?: Record<string, number[]>; // All metric values for this row (input) across versions
  agentId?: string;
};

function CompletionCell(props: CompletionCellProps) {
  const { completion, annotations, experimentId, allMetricsPerKey, agentId } = props;
  const router = useRouter();
  const searchParams = useSearchParams();
  const { showToast } = useToast();
  const [isHovered, setIsHovered] = useState(false);

  const filteredAnnotations = useMemo(() => {
    return annotations?.filter((annotation) => annotation.target?.completion_id === completion?.id);
  }, [annotations, completion?.id]);

  const completionMetrics = useMemo(() => {
    if (!annotations || !completion?.id) return [];
    return getMetricsForCompletion(annotations, completion.id);
  }, [annotations, completion?.id]);

  const allMetrics = useMemo(() => {
    const metrics: Array<{ key: string; average: number }> = [];

    // Add cost metric if valid using centralized utility
    if (shouldIncludeCostMetric(completion)) {
      metrics.push({ key: "cost", average: completion.cost_usd });
    }

    // Add duration metric if valid using centralized utility
    if (shouldIncludeDurationMetric(completion)) {
      metrics.push({ key: "duration", average: completion.duration_seconds });
    }

    // Add custom metrics from annotations
    if (completionMetrics.length > 0) {
      metrics.push(...completionMetrics);
    }

    return metrics;
  }, [completion, completionMetrics]);

  const allMetricsPerKeyForCompletion = allMetricsPerKey || {};

  const openCompletionModal = () => {
    if (!completion?.id) return;

    const params = new URLSearchParams(searchParams);
    params.set("showCompletionModal", completion.id);
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    router.replace(newUrl, { scroll: false });
  };

  const handleCopyCompletion = async () => {
    if (!completion?.id) return;

    const completionPath = `anotherai/completion/${completion.id}`;
    try {
      await navigator.clipboard.writeText(completionPath);
      showToast("Copied to clipboard");
    } catch (err) {
      console.error("Failed to copy: ", err);
      showToast("Failed to copy");
    }
  };

  const [keypathSelected, setKeypathSelected] = useState<string | null>(null);

  if (!completion) {
    return <div className="text-xs text-gray-400 italic text-center py-8">No completion found</div>;
  }

  return (
    <div
      className="flex flex-col h-full max-h-[800px]"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex-1 space-y-3 overflow-y-auto">
        {/* Error Display */}
        {completion.output?.error && <PageError error={completion.output.error} />}

        {/* Messages Display */}
        {completion.output?.messages && completion.output.messages.length > 0 && (
          <div className="h-max">
            <MessagesViewer
              messages={completion.output.messages}
              annotations={filteredAnnotations}
              onKeypathSelect={(keyPath) => setKeypathSelected(keyPath)}
            />
          </div>
        )}

        {/* Annotations Display */}
        <div className="h-max">
          <AnnotationsView
            annotations={annotations}
            completionId={completion.id}
            experimentId={experimentId}
            showAddButton={true}
            keypathSelected={keypathSelected}
            setKeypathSelected={setKeypathSelected}
            agentId={agentId}
          />
        </div>
      </div>

      {/* Metrics Display at bottom */}
      {allMetrics.length > 0 && (
        <div className="pt-3 border-t border-gray-200 mt-3">
          <MetricsDisplay
            metrics={allMetrics}
            allMetricsPerKey={allMetricsPerKeyForCompletion}
            showAvgPrefix={false}
            className="space-y-1"
            usePer1kMultiplier={false}
          />
        </div>
      )}

      {/* Open completion modal button and copy button */}
      <div className="pt-1 mt-1 flex gap-1 items-center">
        <button
          onClick={openCompletionModal}
          className="flex-1 px-3 h-8 text-xs font-semibold text-gray-500 hover:text-gray-700 hover:bg-gray-50 border border-gray-200 rounded transition-colors flex items-center justify-center cursor-pointer"
          title="Open completion details"
        >
          View Details
        </button>
        {isHovered && (
          <HoverPopover
            content={<div className="text-xs">Copy Completion ID</div>}
            position="top"
            popoverClassName="bg-gray-800 text-white rounded-[4px] px-2 py-1"
          >
            <button
              onClick={handleCopyCompletion}
              className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer h-8 w-8 rounded flex items-center justify-center"
            >
              <Copy size={12} />
            </button>
          </HoverPopover>
        )}
      </div>
    </div>
  );
}

// Helper function to compare ExperimentCompletion objects
function areCompletionsEqual(prev?: ExperimentCompletion, next?: ExperimentCompletion): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;

  return (
    prev.id === next.id &&
    prev.cost_usd === next.cost_usd &&
    prev.duration_seconds === next.duration_seconds &&
    prev.output === next.output
  );
}

// Helper function to compare number arrays
function areNumberArraysEqual(prev?: number[], next?: number[]): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i] !== next[i]) return false;
  }
  return true;
}

// Helper function to compare Annotation arrays
function areAnnotationsEqual(prev?: Annotation[], next?: Annotation[]): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i].id !== next[i].id || prev[i].text !== next[i].text || prev[i].target !== next[i].target) {
      return false;
    }
  }
  return true;
}

// Helper function to compare metrics per key objects
function areMetricsPerKeyForRowEqual(prev?: Record<string, number[]>, next?: Record<string, number[]>): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;

  const prevKeys = Object.keys(prev);
  const nextKeys = Object.keys(next);

  if (prevKeys.length !== nextKeys.length) return false;

  for (const key of prevKeys) {
    if (!areNumberArraysEqual(prev[key], next[key])) return false;
  }

  return true;
}

export default memo(CompletionCell, (prevProps, nextProps) => {
  return (
    areCompletionsEqual(prevProps.completion, nextProps.completion) &&
    prevProps.experimentId === nextProps.experimentId &&
    prevProps.agentId === nextProps.agentId &&
    areAnnotationsEqual(prevProps.annotations, nextProps.annotations) &&
    areMetricsPerKeyForRowEqual(prevProps.allMetricsPerKey, nextProps.allMetricsPerKey)
  );
});
