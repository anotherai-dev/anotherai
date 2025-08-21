import { Copy } from "lucide-react";
import { useMemo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { useToast } from "@/components/ToastProvider";
import {
  findIndexOfVersionThatFirstUsedThosePrompt,
  findIndexOfVersionThatFirstUsedThosePromptAndSchema,
  findIndexOfVersionThatFirstUsedThoseSchema,
} from "@/components/utils/utils";
import { VersionDetailsView } from "@/components/version-details/VersionDetailsView";
import { Annotation, Message, Version } from "@/types/models";
import { VersionHeaderMetrics } from "./VersionHeaderMetrics";
import { VersionHeaderModel } from "./VersionHeaderModel";
import { VersionHeaderPriceAndLatency } from "./VersionHeaderPriceAndLatency";
import { VersionHeaderPrompt } from "./VersionHeaderPrompt";
import { VersionHeaderSchema } from "./VersionHeaderSchema";
import { VersionHeaderSharedPromptAndSchema } from "./VersionHeaderSharedPromptAndSchema";
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
    versionCosts: number[];
    versionDurations: number[];
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

  const [isHovered, setIsHovered] = useState(false);
  const { showToast } = useToast();

  const handleCopyVersion = async () => {
    const versionPath = `anotherai/version/${version.id}`;
    try {
      await navigator.clipboard.writeText(versionPath);
      showToast("Copied to clipboard");
    } catch (err) {
      console.error("Failed to copy: ", err);
      showToast("Failed to copy");
    }
  };

  const optionalKeysToShowWithoutPromptAndOutputSchema = useMemo(() => {
    return optionalKeysToShow.filter((key) => key !== "prompt" && key !== "output_schema");
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
      const indexOfVersionThatFirstUsedThosePromptAndSchema = findIndexOfVersionThatFirstUsedThosePromptAndSchema(
        versions,
        version
      );
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
          indexOfVersionThatFirstUsedThosePromptAndSchema,
        };
      }
    }

    return { showCombined: false, showPrompt, showSchema };
  }, [versions, version, optionalKeysToShow, index]);

  return (
    <div className="flex flex-col h-full text-xs">
      <div className="flex-1 space-y-2">
        <div onMouseEnter={() => setIsHovered(true)} onMouseLeave={() => setIsHovered(false)}>
          <HoverPopover
            content={<VersionDetailsView version={version} showPrompt={false} />}
            position="bottom"
            popoverClassName="rounded bg-white border border-gray-200 w-80"
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="text-gray-800 font-semibold text-sm cursor-pointer hover:text-gray-600">
                Version {index + 1}
              </div>
              {isHovered && (
                <button
                  onClick={handleCopyVersion}
                  className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer h-5 w-5 rounded-[2px] flex items-center justify-center"
                  title="Copy version ID"
                >
                  <Copy size={12} />
                </button>
              )}
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
            indexOfVersionThatFirstUsedThosePromptAndSchema={
              promptAndSchemaLogic.indexOfVersionThatFirstUsedThosePromptAndSchema!
            }
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
          <VersionHeaderPriceAndLatency priceAndLatency={priceAndLatency} showAvgPrefix={showAvgPrefix} />
          <VersionHeaderMetrics metrics={metrics} allMetricsPerKey={allMetricsPerKey} showAvgPrefix={showAvgPrefix} />
        </div>
      )}
    </div>
  );
}
