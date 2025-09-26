import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { VersionDetailsView } from "@/components/version-details/VersionDetailsView";
import { Annotation, Completion } from "@/types/models";
import { AnnotationsPromptLabel } from "../annotations/AnnotationsPromptLabel";
import InfoRow from "./InfoRow";
import MetadataView from "./MetadataView";
import { TracesView } from "./TracesView";

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
          {completion.created_at && (
            <InfoRow title="Created" value={new Date(completion.created_at).toLocaleString()} />
          )}
          <InfoRow
            title="Version ID"
            value={completion.version.id}
            copyValue={`anotherai/version/${completion.version.id}`}
            copyable={true}
          />

          <VersionDetailsView
            version={completion.version}
            showPrompt={true}
            showOutputSchema={true}
            showExamples={true}
          />
        </div>

        <TracesView traces={completion.traces} />

        <MetadataView metadata={completion.metadata} />
      </div>
    </div>
  );
}
