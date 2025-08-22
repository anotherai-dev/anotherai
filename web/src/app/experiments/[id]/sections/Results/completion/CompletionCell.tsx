import { Copy } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { PageError } from "@/components/PageError";
import { PriceAndLatencyDisplay } from "@/components/PriceAndLatencyDisplay";
import { useToast } from "@/components/ToastProvider";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { Annotation, ExperimentCompletion } from "@/types/models";
import { getMetricsForCompletion } from "../../../utils";
import { CompletionMetrics } from "./CompletionMetrics";

export type CompletionCellProps = {
  completion: ExperimentCompletion | undefined;
  allCosts?: number[];
  allDurations?: number[];
  annotations?: Annotation[]; // All annotations from experiment
  experimentId?: string;
  allMetricsPerKeyForRow?: Record<string, number[]>; // All metric values for this row (input) across versions
  agentId?: string;
};

export function CompletionCell(props: CompletionCellProps) {
  const { completion, allCosts, allDurations, annotations, experimentId, allMetricsPerKeyForRow, agentId } = props;
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

      {/* Price, Latency and Metrics Display at bottom */}
      {((completion.cost_usd !== undefined && completion.duration_seconds !== undefined) ||
        completionMetrics.length > 0) && (
        <div className="pt-3 border-t border-gray-200 mt-3 space-y-1">
          {completion.cost_usd !== undefined && completion.duration_seconds !== undefined && (
            <PriceAndLatencyDisplay
              cost={completion.cost_usd}
              duration={completion.duration_seconds}
              allCosts={allCosts}
              allDurations={allDurations}
            />
          )}
          <CompletionMetrics metrics={completionMetrics} allMetricsPerKeyForRow={allMetricsPerKeyForRow} />
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
