import { memo, useMemo } from "react";
import {
  createOutputSchemaFromJSON,
  getVersionKeyDisplayName,
  isJSONSchema,
  parseJSONValue,
} from "@/components/utils/utils";
import { Annotation, ExtendedVersion, Message, OutputSchema, Tool } from "@/types/models";
import { VersionPromptSection } from "../Results/version/VersionPromptSection";
import { VersionSchemaSection } from "../Results/version/VersionSchemaSection";
import MatchingBaseValue from "./MatchingBaseValue";
import MatchingJSONValue from "./MatchingJSONValue";
import MatchingToolValue from "./MatchingToolValue";

type MatchingRowProps = {
  keyName: string;
  versionWithDefaults: ExtendedVersion;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  agentId?: string;
};

function MatchingRow({
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
  const rawValue = (versionWithDefaults as unknown as Record<string, unknown>)[keyName];
  const parsedJSON = parseJSONValue(rawValue);
  const isSchemaDetected = useMemo(() => isJSONSchema(parsedJSON), [parsedJSON]);

  // Memoized OutputSchema creation for JSON schemas
  const outputSchema = useMemo(() => {
    return isSchemaDetected ? createOutputSchemaFromJSON(parsedJSON, keyName || "detected-schema") : null;
  }, [isSchemaDetected, parsedJSON, keyName]);

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
    }

    // Handle JSON schema detection outside the switch
    if (outputSchema) {
      return (
        <VersionSchemaSection
          outputSchema={outputSchema}
          annotations={annotations}
          experimentId={experimentId}
          completionId={completionId}
          prefix={keyName}
          className="mt-2 space-y-3 px-2"
          agentId={agentId}
        />
      );
    }

    // Default case - Use MatchingJSONValue if JSON is detected, otherwise use MatchingBaseValue
    if (parsedJSON !== null) {
      return (
        <MatchingJSONValue
          value={rawValue}
          parsedJSON={parsedJSON}
          annotations={annotations}
          experimentId={experimentId}
          completionId={completionId}
          keyPath={keyName}
          containerPadding="px-2 py-2"
        />
      );
    }
    return (
      <MatchingBaseValue
        value={rawValue}
        annotations={annotations}
        experimentId={experimentId}
        completionId={completionId}
        keyPath={keyName}
      />
    );
  };

  return (
    <div className="flex border-b border-gray-200/60 last:border-b-0 mx-[8px]">
      <div className="w-54 px-2 py-[12px] text-xs font-semibold text-gray-900">{displayName}</div>
      <div className="flex-1 text-xs text-gray-900 items-center px-2">{renderValue()}</div>
    </div>
  );
}

// Helper function to compare ExtendedVersion objects
function areExtendedVersionsEqual(prev: ExtendedVersion, next: ExtendedVersion): boolean {
  return (
    prev.id === next.id &&
    prev.model === next.model &&
    prev.prompt === next.prompt &&
    prev.output_schema === next.output_schema &&
    prev.tools === next.tools &&
    prev.reasoning_effort === next.reasoning_effort &&
    prev.reasoning_budget === next.reasoning_budget
  );
}

// Helper function to compare Annotation arrays
function areAnnotationsEqual(prev?: Annotation[], next?: Annotation[]): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i].id !== next[i].id || prev[i].text !== next[i].text) {
      return false;
    }
  }
  return true;
}

export default memo(MatchingRow, (prevProps, nextProps) => {
  return (
    prevProps.keyName === nextProps.keyName &&
    areExtendedVersionsEqual(prevProps.versionWithDefaults, nextProps.versionWithDefaults) &&
    prevProps.experimentId === nextProps.experimentId &&
    prevProps.completionId === nextProps.completionId &&
    prevProps.agentId === nextProps.agentId &&
    areAnnotationsEqual(prevProps.annotations, nextProps.annotations)
  );
});
