import { HoverPopover } from "@/components/HoverPopover";
import { Annotation } from "@/types/models";
import { UpdateAgentTooltip } from "./UpdateAgentTooltip";

type AnnotationsPromptLabelProps = {
  annotations?: Annotation[];
  agentId?: string;
  experimentId?: string;
};

export function AnnotationsPromptLabel(props: AnnotationsPromptLabelProps) {
  const { annotations, agentId, experimentId } = props;

  if (!annotations || annotations.length === 0 || !agentId) {
    return null;
  }

  return (
    <HoverPopover
      content={<UpdateAgentTooltip agentId={agentId} experimentId={experimentId} />}
      position="bottom"
      popoverClassName="bg-gray-900 rounded-md overflow-hidden px-2 py-1"
    >
      <div className="px-3 py-2 text-xs text-gray-500 font-normal underline-offset-2 underline cursor-pointer whitespace-pre-wrap text-right hover:text-gray-70 rounded transition-colors">
        Update agent with annotations
      </div>
    </HoverPopover>
  );
}
