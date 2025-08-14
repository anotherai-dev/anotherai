import { useMemo } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { VersionPromptAndSchemaDetails } from "@/components/VersionPromptAndSchemaDetails";
import { findIndexOfVersionThatFirstUsedThoseSchema } from "@/components/utils/utils";
import { Annotation, Message, Version } from "@/types/models";
import { VersionSchemaSection } from "./VersionSchemaSection";

type VersionHeaderSchemaProps = {
  version: Version;
  sharedPartsOfPrompts?: Message[];
  sharedKeypathsOfSchemas?: string[];
  versions?: Version[];
  index: number;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  agentId?: string;
};

export function VersionHeaderSchema(props: VersionHeaderSchemaProps) {
  const {
    version,
    sharedPartsOfPrompts,
    sharedKeypathsOfSchemas,
    versions,
    index,
    annotations,
    experimentId,
    completionId,
    agentId,
  } = props;

  const indexOfVersionThatFirstUsedThisSchema = useMemo(() => {
    if (!versions || versions.length === 0) {
      return undefined;
    }
    return findIndexOfVersionThatFirstUsedThoseSchema(versions, version);
  }, [versions, version]);

  // If reusing schema from another version, show badge instead
  if (
    indexOfVersionThatFirstUsedThisSchema !== undefined &&
    indexOfVersionThatFirstUsedThisSchema !== index
  ) {
    return (
      <>
        <div className="mt-3 pt-4 border-t border-gray-200">
          <HoverPopover
            content={
              <VersionPromptAndSchemaDetails
                version={version}
                sharedPartsOfPrompts={sharedPartsOfPrompts}
                sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
              />
            }
            position="bottom"
            popoverClassName="rounded bg-white border border-gray-200 p-3 w-[32rem]"
          >
            <div className="inline-block px-2 py-2 text-xs rounded-[2px] font-medium bg-gray-100 border border-gray-300 text-gray-700 leading-loose hover:bg-gray-200">
              Same output schema as{" "}
              <span className="inline-block px-2 py-1 text-xs rounded font-medium bg-gray-200 border border-gray-300 text-gray-900">
                Version {indexOfVersionThatFirstUsedThisSchema + 1}
              </span>
            </div>
          </HoverPopover>
        </div>
      </>
    );
  }

  if (
    !version.output_schema ||
    Object.keys(version.output_schema).length === 0
  ) {
    return null;
  }

  return (
    <>
      <div className="mt-3 pt-2 border-t border-gray-200" />
      <div className="text-gray-600 font-medium text-xs mb-2">
        Output Schema
      </div>
      <VersionSchemaSection
        outputSchema={version.output_schema}
        sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
        annotations={annotations}
        experimentId={experimentId}
        completionId={completionId}
        prefix={`versions.${index}.output_schema`}
        className="space-y-2"
        agentId={agentId}
      />
    </>
  );
}
