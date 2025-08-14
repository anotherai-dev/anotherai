import { useMemo } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { VersionPromptAndSchemaDetails } from "@/components/VersionPromptAndSchemaDetails";
import { findIndexOfVersionThatFirstUsedThosePrompt } from "@/components/utils/utils";
import { Annotation, Message, Version } from "@/types/models";
import { VersionPromptSection } from "./VersionPromptSection";

type VersionHeaderPromptProps = {
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

export function VersionHeaderPrompt(props: VersionHeaderPromptProps) {
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

  const indexOfVersionThatFirstUsedThisPrompt = useMemo(() => {
    if (!versions || versions.length === 0) {
      return undefined;
    }
    return findIndexOfVersionThatFirstUsedThosePrompt(versions, version);
  }, [versions, version]);

  // If reusing prompt from another version, show badge instead
  if (
    indexOfVersionThatFirstUsedThisPrompt !== undefined &&
    indexOfVersionThatFirstUsedThisPrompt !== index
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
              Same prompt as{" "}
              <span className="inline-block px-2 py-1 text-xs rounded font-medium bg-gray-200 border border-gray-300 text-gray-900">
                Version {indexOfVersionThatFirstUsedThisPrompt + 1}
              </span>
            </div>
          </HoverPopover>
        </div>
      </>
    );
  }

  if (!version.prompt || version.prompt.length === 0) {
    return null;
  }

  return (
    <>
      <div className="mt-3 pt-2 border-t border-gray-200" />
      <div className="text-gray-600 font-medium text-xs mb-2">Prompt</div>
      <VersionPromptSection
        prompt={version.prompt}
        sharedPartsOfPrompts={sharedPartsOfPrompts}
        annotations={annotations}
        experimentId={experimentId}
        completionId={completionId}
        prefix={`versions.${index}.prompt`}
        className="space-y-2"
        agentId={agentId}
      />
    </>
  );
}