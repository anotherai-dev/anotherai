import { getVersionKeyDisplayName } from "@/components/utils/utils";
import {
  Annotation,
  ExtendedVersion,
  Message,
  OutputSchema,
  Tool,
} from "@/types/models";
import { VersionPromptSection } from "../Results/version/VersionPromptSection";
import { VersionSchemaSection } from "../Results/version/VersionSchemaSection";
import { MatchingBaseValue } from "./MatchingBaseValue";
import { MatchingToolValue } from "./MatchingToolValue";

type MatchingRowProps = {
  keyName: string;
  versionWithDefaults: ExtendedVersion;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  agentId?: string;
};

export function MatchingRow({
  keyName,
  versionWithDefaults,
  annotations,
  experimentId,
  completionId,
  agentId,
}: MatchingRowProps) {
  // Get display name for the key
  const displayName = getVersionKeyDisplayName(keyName);
  // Extract the raw value
  const rawValue = (versionWithDefaults as unknown as Record<string, unknown>)[
    keyName
  ];

  // Render appropriate component based on key type
  const renderValue = () => {
    switch (keyName) {
      case "prompt":
        return (
          <VersionPromptSection
            prompt={rawValue as Message[]}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            prefix={keyName}
            className="mt-2 space-y-3 px-2"
            agentId={agentId}
          />
        );
      case "output_schema":
        return (
          <VersionSchemaSection
            outputSchema={rawValue as OutputSchema}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            prefix={keyName}
            className="mt-2 space-y-3 px-2"
            agentId={agentId}
          />
        );
      case "tools":
        return (
          <MatchingToolValue
            tools={rawValue as Tool[]}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            keyPath={keyName}
          />
        );
      default:
        return (
          <MatchingBaseValue
            value={rawValue}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            keyPath={keyName}
          />
        );
    }
  };

  return (
    <div className="flex border-b border-gray-200/60 last:border-b-0 mx-[8px]">
      <div className="w-54 px-2 py-[12px] text-xs font-semibold text-gray-900">
        {displayName}
      </div>
      <div className="flex-1 text-xs text-gray-900 items-center px-2">
        {renderValue()}
      </div>
    </div>
  );
}
