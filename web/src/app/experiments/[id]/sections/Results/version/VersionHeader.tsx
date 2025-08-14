import { useMemo } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { VersionDetailsView } from "@/components/version-details/VersionDetailsView";
import { Annotation, Message, Version } from "@/types/models";
import { 
  findIndexOfVersionThatFirstUsedThosePromptAndSchema,
  findIndexOfVersionThatFirstUsedThosePrompt,
  findIndexOfVersionThatFirstUsedThoseSchema
} from "@/components/utils/utils";
import { VersionHeaderMetrics } from "./VersionHeaderMetrics";
import { VersionHeaderModel } from "./VersionHeaderModel";
import { VersionHeaderPriceAndLatency } from "./VersionHeaderPriceAndLatency";
import { VersionHeaderPrompt } from "./VersionHeaderPrompt";
import { VersionHeaderSharedPromptAndSchema } from "./VersionHeaderSharedPromptAndSchema";
import { VersionHeaderSchema } from "./VersionHeaderSchema";
import { VersionOptionalKeysView } from "./VersionOptionalKeysView";

type VersionHeaderProps = {
  version: Version;
  optionalKeysToShow: string[];
  index: number;
  priceAndLatency?: {
    avgCost: number;
    avgDuration: number;
    allCosts: number[];
    allDurations: number[];
  };
  versions?: Version[];
  sharedPartsOfPrompts?: Message[];
  sharedKeypathsOfSchemas?: string[];
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
  metrics?: { key: string; average: number }[];
  allMetricsPerKey?: Record<string, number[]>;
  showAvgPrefix?: boolean;
  agentId?: string;
};

export function VersionHeader(props: VersionHeaderProps) {
  const {
    version,
    optionalKeysToShow,
    index,
    priceAndLatency,
    versions,
    sharedPartsOfPrompts,
    sharedKeypathsOfSchemas,
    annotations,
    experimentId,
    completionId,
    metrics,
    allMetricsPerKey,
    showAvgPrefix = true,
    agentId,
  } = props;

  const optionalKeysToShowWithoutPromptAndOutputSchema = useMemo(() => {
    return optionalKeysToShow.filter(
      (key) => key !== "prompt" && key !== "output_schema"
    );
  }, [optionalKeysToShow]);

  const promptAndSchemaLogic = useMemo(() => {
    if (!versions || versions.length === 0) {
      return { showCombined: false, showPrompt: false, showSchema: false };
    }

    const showPrompt = optionalKeysToShow.includes("prompt");
    const showSchema = optionalKeysToShow.includes("output_schema");
    
    if (!showPrompt && !showSchema) {
      return { showCombined: false, showPrompt: false, showSchema: false };
    }

    // If showing both, check if they match the same version
    if (showPrompt && showSchema) {
      const indexOfVersionThatFirstUsedThosePromptAndSchema = findIndexOfVersionThatFirstUsedThosePromptAndSchema(versions, version);
      const indexOfVersionThatFirstUsedThosePrompt = findIndexOfVersionThatFirstUsedThosePrompt(versions, version);
      const indexOfVersionThatFirstUsedThoseSchema = findIndexOfVersionThatFirstUsedThoseSchema(versions, version);
      
      // If both match and they match the same version (and not current), show combined
      if (
        indexOfVersionThatFirstUsedThosePromptAndSchema !== undefined &&
        indexOfVersionThatFirstUsedThosePromptAndSchema !== index &&
        indexOfVersionThatFirstUsedThosePrompt === indexOfVersionThatFirstUsedThosePromptAndSchema &&
        indexOfVersionThatFirstUsedThoseSchema === indexOfVersionThatFirstUsedThosePromptAndSchema
      ) {
        return { 
          showCombined: true, 
          showPrompt: false, 
          showSchema: false,
          indexOfVersionThatFirstUsedThosePromptAndSchema
        };
      }
    }

    return { showCombined: false, showPrompt, showSchema };
  }, [versions, version, optionalKeysToShow, index]);

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="flex-1 space-y-2">
        <div>
          <HoverPopover
            content={
              <VersionDetailsView version={version} showPrompt={false} />
            }
            position="bottom"
            popoverClassName="rounded bg-white border border-gray-200 w-80"
          >
            <div className="text-gray-800 font-semibold mb-2 text-sm cursor-pointer hover:text-gray-600">
              Version {index + 1}
            </div>
          </HoverPopover>
          <VersionHeaderModel
            version={version}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            index={index}
          />
        </div>

        <VersionOptionalKeysView
          version={version}
          optionalKeysToShow={optionalKeysToShowWithoutPromptAndOutputSchema}
          annotations={annotations}
          experimentId={experimentId}
          completionId={completionId}
          index={index}
        />

        {promptAndSchemaLogic.showCombined && (
          <VersionHeaderSharedPromptAndSchema
            version={version}
            sharedPartsOfPrompts={sharedPartsOfPrompts}
            sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
            versions={versions}
            index={index}
            indexOfVersionThatFirstUsedThosePromptAndSchema={promptAndSchemaLogic.indexOfVersionThatFirstUsedThosePromptAndSchema!}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            agentId={agentId}
          />
        )}

        {promptAndSchemaLogic.showPrompt && (
          <VersionHeaderPrompt
            version={version}
            sharedPartsOfPrompts={sharedPartsOfPrompts}
            sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
            versions={versions}
            index={index}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            agentId={agentId}
          />
        )}

        {promptAndSchemaLogic.showSchema && (
          <VersionHeaderSchema
            version={version}
            sharedPartsOfPrompts={sharedPartsOfPrompts}
            sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
            versions={versions}
            index={index}
            annotations={annotations}
            experimentId={experimentId}
            completionId={completionId}
            agentId={agentId}
          />
        )}
      </div>

      {(priceAndLatency || metrics) && (
        <div className="mt-auto">
          <div className="mt-3 pt-2 border-t border-gray-200" />
          <VersionHeaderPriceAndLatency
            priceAndLatency={priceAndLatency}
            showAvgPrefix={showAvgPrefix}
          />
          <VersionHeaderMetrics
            metrics={metrics}
            allMetricsPerKey={allMetricsPerKey}
            showAvgPrefix={showAvgPrefix}
          />
        </div>
      )}
    </div>
  );
}
