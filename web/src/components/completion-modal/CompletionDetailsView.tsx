import { Copy } from "lucide-react";
import { useState } from "react";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { VersionDetailsView } from "@/components/version-details/VersionDetailsView";
import { Annotation, Completion } from "@/types/models";
import { useToast } from "../ToastProvider";
import { AnnotationsPromptLabel } from "../annotations/AnnotationsPromptLabel";
import { MetadataView } from "./MetadataView";

type InfoRowProps = {
  title: string;
  value: string;
  copyable?: boolean;
  copyValue?: string; // Optional separate value for copying
};

function InfoRow({ title, value, copyable = false, copyValue }: InfoRowProps) {
  const { showToast } = useToast();
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = async () => {
    try {
      // Use copyValue if provided, otherwise use display value
      await navigator.clipboard.writeText(copyValue || value);
      showToast("Copied to clipboard");
    } catch (err) {
      console.error("Failed to copy: ", err);
      showToast("Failed to copy");
    }
  };

  const showCopyButton = copyable && isHovered;

  return (
    <div
      className="bg-white border border-gray-200 rounded-[2px] px-2"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-gray-700 py-2">{title}</span>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-900 py-2">{value}</span>
          {showCopyButton && (
            <button
              onClick={handleCopy}
              className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer h-5 w-5 rounded-[2px] flex items-center justify-center ml-1"
              title="Copy to clipboard"
            >
              <Copy size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

type Props = {
  completion: Completion;
  annotations?: Annotation[];
  keypathSelected?: string | null;
  setKeypathSelected?: (keyPath: string | null) => void;
};

export function CompletionDetailsView(props: Props) {
  const { completion, annotations, keypathSelected, setKeypathSelected } = props;

  return (
    <div className="flex flex-col w-full h-full">
      <div className="text-base font-bold py-3 px-4 border-b border-gray-200 border-dashed text-gray-600">Details</div>

      <div className="pt-4 overflow-y-auto">
        {/* Annotations Display */}
        <div className="mb-4 border-b border-gray-200 border-dashed pb-2 px-4">
          <div className="flex flex-row justify-between items-center mb-2">
            <div className="text-xs font-medium text-gray-400">Annotations</div>
            <AnnotationsPromptLabel annotations={annotations} agentId={completion.agent_id} />
          </div>
          <AnnotationsView
            annotations={annotations}
            completionId={completion.id}
            showAddButton={true}
            alwaysShowAddForm={true}
            keypathSelected={keypathSelected}
            setKeypathSelected={setKeypathSelected}
            agentId={completion.agent_id}
          />
        </div>

        <div className="space-y-2 px-4">
          <InfoRow title="Agent ID" value={completion.agent_id} />
          <InfoRow
            title="Version ID"
            value={completion.version.id}
            copyValue={`anotherai/agents/${completion.agent_id}/versions/${completion.version.id}`}
            copyable={true}
          />

          <VersionDetailsView version={completion.version} showPrompt={true} showOutputSchema={true} />
        </div>

        <MetadataView metadata={completion.metadata} />
      </div>
    </div>
  );
}
