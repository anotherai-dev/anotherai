import { SchemaViewer } from "@/components/SchemaViewer";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { Message, Version } from "@/types/models";

type VersionPromptAndSchemaDetailsProps = {
  version: Version;
  sharedPartsOfPrompts?: Message[];
  sharedKeypathsOfSchemas?: string[];
};

export function VersionPromptAndSchemaDetails(props: VersionPromptAndSchemaDetailsProps) {
  const { version, sharedPartsOfPrompts, sharedKeypathsOfSchemas } = props;

  const hasPrompt = version.prompt && version.prompt.length > 0;
  const hasSchema = version.output_schema && Object.keys(version.output_schema).length > 0;

  if (!hasPrompt && !hasSchema) {
    return <div className="text-xs text-gray-500 italic">No prompt or output schema defined</div>;
  }

  return (
    <div className="w-full max-w-2xl space-y-3 px-2 py-2">
      {hasPrompt && version.prompt && (
        <div>
          <div className="text-gray-600 font-medium text-xs mb-2">Prompt</div>
          <div className="overflow-y-auto max-h-60">
            <MessagesViewer messages={version.prompt} sharedPartsOfPrompts={sharedPartsOfPrompts} />
          </div>
        </div>
      )}

      {hasSchema && version.output_schema && (
        <div>
          {hasPrompt && <div className="border-t border-gray-200 pt-3" />}
          <div className="text-gray-600 font-medium text-xs mb-2">Output Schema</div>
          <div>
            <SchemaViewer schema={version.output_schema} sharedKeypathsOfSchemas={sharedKeypathsOfSchemas} />
          </div>
        </div>
      )}
    </div>
  );
}
