import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { Annotation, Message } from "@/types/models";

type VersionPromptSectionProps = {
  prompt: Message[];
  sharedPartsOfPrompts?: Message[];
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  prefix?: string;
  className?: string;
  agentId?: string;
};

export function VersionPromptSection(props: VersionPromptSectionProps) {
  const { prompt, sharedPartsOfPrompts, annotations, experimentId, completionId, prefix, className, agentId } = props;

  return (
    <div className={className}>
      <div className="overflow-y-auto max-h-80">
        <MessagesViewer messages={prompt} sharedPartsOfPrompts={sharedPartsOfPrompts} annotations={annotations} />
      </div>
      <AnnotationsView
        annotations={annotations}
        keyPathPrefix={prefix}
        experimentId={experimentId}
        completionId={completionId}
        showAddButton={true}
        agentId={agentId}
      />
    </div>
  );
}
