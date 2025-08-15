import { HoverPopover } from "@/components/HoverPopover";
import { VersionPromptAndSchemaDetails } from "@/components/VersionPromptAndSchemaDetails";
import { Annotation, Message, Version } from "@/types/models";

type VersionHeaderSharedPromptAndSchemaProps = {
  version: Version;
  sharedPartsOfPrompts?: Message[];
  sharedKeypathsOfSchemas?: string[];
  versions?: Version[];
  index: number;
  indexOfVersionThatFirstUsedThosePromptAndSchema: number;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  agentId?: string;
};

export function VersionHeaderSharedPromptAndSchema(props: VersionHeaderSharedPromptAndSchemaProps) {
  const { version, sharedPartsOfPrompts, sharedKeypathsOfSchemas, indexOfVersionThatFirstUsedThosePromptAndSchema } =
    props;

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
            Same prompt and output schema as{" "}
            <span className="inline-block px-2 py-1 text-xs rounded font-medium bg-gray-200 border border-gray-300 text-gray-900">
              Version {indexOfVersionThatFirstUsedThosePromptAndSchema + 1}
            </span>
          </div>
        </HoverPopover>
      </div>
    </>
  );
}
