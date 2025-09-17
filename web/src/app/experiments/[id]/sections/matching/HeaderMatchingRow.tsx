import { useMemo } from "react";
import {
  createOutputSchemaFromJSON,
  getVersionKeyDisplayName,
  isJSONSchema,
  parseJSONValue,
} from "@/components/utils/utils";
import { Annotation, ExtendedVersion, Message, OutputSchema, Tool } from "@/types/models";
import { VersionPromptSection } from "../Results/version/VersionPromptSection";
import { VersionSchemaSection } from "../Results/version/VersionSchemaSection";
import { MatchingBaseValue } from "./MatchingBaseValue";
import { MatchingJSONValue } from "./MatchingJSONValue";
import { MatchingToolValue } from "./MatchingToolValue";

type HeaderMatchingRowProps = {
  keyName: string;
  versionWithDefaults: ExtendedVersion;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  agentId?: string;
};

export function HeaderMatchingRow({
  keyName,
  versionWithDefaults,
  annotations,
  experimentId,
  completionId,
  agentId,
}: HeaderMatchingRowProps) {
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
            className="mt-2 space-y-3"
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
            position="topRight"
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
          className="mt-2 space-y-3"
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
          position="topRight"
          containerPadding="pt-1"
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
        supportMultiline={true}
        position="topRight"
      />
    );
  };

  // Special layout for prompt, output_schema, JSON schemas, and JSON values - keep header style (key above value)
  if (
    keyName === "prompt" ||
    keyName === "output_schema" ||
    isSchemaDetected ||
    (parsedJSON !== null && keyName !== "tools")
  ) {
    return (
      <div className="border-b border-gray-200/60 last:border-b-0 mx-[8px] py-2">
        <div className="pb-1 text-xs font-medium text-gray-600">{displayName}</div>
        <div className="text-xs text-gray-900">{renderValue()}</div>
      </div>
    );
  }

  // Default layout for all other keys - justify between (key far left, value far right)
  return (
    <div className="flex justify-between border-b border-gray-200/60 last:border-b-0 mx-[8px] overflow-hidden">
      <div className="text-xs font-medium text-gray-600 pt-3.5">{displayName}</div>
      <div className="text-xs text-gray-900">{renderValue()}</div>
    </div>
  );
}
