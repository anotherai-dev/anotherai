import { Copy } from "lucide-react";
import { useMemo, useState } from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { useToast } from "@/components/ToastProvider";
import { DeployVersionInstructions } from "@/components/experiment/DeployVersionInstructions";
import {
  findIndexOfVersionThatFirstUsedThosePrompt,
  findIndexOfVersionThatFirstUsedThosePromptAndSchema,
  findIndexOfVersionThatFirstUsedThoseSchema,
} from "@/components/utils/utils";
import { Annotation, ExperimentWithLookups, Message, Version } from "@/types/models";
import { HeaderMatchingSection } from "../../matching/HeaderMatchingSection";
import { DraggableColumnWrapper } from "./DraggableColumnWrapper";
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
  experiment?: ExperimentWithLookups;
  // Drag and drop props
  onReorderColumns?: (fromIndex: number, toIndex: number) => void;
  dragIndex?: number;
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
    experiment,
    onReorderColumns,
    dragIndex,
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
    <DraggableColumnWrapper
      onReorderColumns={onReorderColumns}
      dragIndex={dragIndex}
      versionId={version.id}
      className="firefox-version-header"
    >
      <div className="firefox-version-content">
        <div onMouseEnter={() => setIsHovered(true)} onMouseLeave={() => setIsHovered(false)}>
          <div className="flex items-center gap-2 mb-2">
            <div className="text-gray-800 font-semibold text-sm">Version {index + 1}</div>
            {isHovered && (
              <HoverPopover
                content={<div className="text-xs">Copy Version ID</div>}
                position="top"
                popoverClassName="bg-gray-800 text-white rounded-[4px] px-2 py-1"
              >
                <button
                  onClick={handleCopyVersion}
                  className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer h-5 w-5 rounded-[2px] flex items-center justify-center"
                >
                  <Copy size={12} />
                </button>
              </HoverPopover>
            )}
          </div>
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

        <div className="mt-3">
          <DeployVersionInstructions versionId={version.id} agentId={agentId} />
        </div>

        {experiment && (
          <div className="mt-3">
            <HeaderMatchingSection experiment={experiment} annotations={annotations} experimentId={experimentId} />
          </div>
        )}
      </div>

      <div className="firefox-version-metrics">
        {(priceAndLatency || metrics) && (
          <>
            <div className="pt-2 mt-3 border-t border-gray-200" />
            <VersionHeaderPriceAndLatency priceAndLatency={priceAndLatency} showAvgPrefix={showAvgPrefix} />
            <VersionHeaderMetrics metrics={metrics} allMetricsPerKey={allMetricsPerKey} showAvgPrefix={showAvgPrefix} />
          </>
        )}
      </div>
    </DraggableColumnWrapper>
  );
}
