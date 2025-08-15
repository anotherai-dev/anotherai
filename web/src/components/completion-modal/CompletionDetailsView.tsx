import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { VersionDetailsView } from "@/components/version-details/VersionDetailsView";
import { Annotation, Completion } from "@/types/models";
import { AnnotationsPromptLabel } from "../annotations/AnnotationsPromptLabel";
import { MetadataView } from "./MetadataView";

type InfoRowProps = {
  title: string;
  value: string;
};

function InfoRow({ title, value }: InfoRowProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-[2px] p-2">
      <div className="flex justify-between items-center">
        <span className="text-xs font-medium text-gray-700">{title}</span>
        <span className="text-xs text-gray-900">{value}</span>
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

          <VersionDetailsView version={completion.version} showPrompt={true} showOutputSchema={true} />
        </div>

        <MetadataView metadata={completion.metadata} />
      </div>
    </div>
  );
}
