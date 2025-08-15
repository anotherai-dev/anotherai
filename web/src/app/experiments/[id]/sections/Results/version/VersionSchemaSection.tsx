import { useState } from "react";
import { SchemaViewer } from "@/components/SchemaViewer";
import { AnnotationsView } from "@/components/annotations/AnnotationsView";
import { Annotation, OutputSchema } from "@/types/models";

type VersionSchemaSectionProps = {
  outputSchema: OutputSchema;
  sharedKeypathsOfSchemas?: string[];
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  prefix?: string;
  className?: string;
  agentId?: string;
};

export function VersionSchemaSection(props: VersionSchemaSectionProps) {
  const { outputSchema, sharedKeypathsOfSchemas, annotations, experimentId, completionId, prefix, className, agentId } =
    props;
  const [keypathSelected, setKeypathSelected] = useState<string | null>(null);

  const handleKeypathSelect = (keyPath: string) => {
    setKeypathSelected(keyPath);
  };

  return (
    <div className={className}>
      <SchemaViewer
        schema={outputSchema}
        sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
        annotations={annotations}
        annotationPrefix={prefix}
        onKeypathSelect={handleKeypathSelect}
      />
      <AnnotationsView
        annotations={annotations}
        keyPathPrefix={prefix}
        experimentId={experimentId}
        completionId={completionId}
        showAddButton={true}
        keypathSelected={keypathSelected}
        setKeypathSelected={setKeypathSelected}
        agentId={agentId}
      />
    </div>
  );
}
