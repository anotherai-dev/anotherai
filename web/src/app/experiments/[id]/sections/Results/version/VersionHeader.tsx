import { Copy } from "lucide-react";
import { memo, useMemo, useState } from "react";
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
import VersionHeaderMetrics from "./VersionHeaderMetrics";
import VersionHeaderModel from "./VersionHeaderModel";
import VersionHeaderPriceAndLatency from "./VersionHeaderPriceAndLatency";
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

function VersionHeader(props: VersionHeaderProps) {
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

// Helper function to compare Version objects
function areVersionsEqual(prev: Version, next: Version): boolean {
  return (
    prev.id === next.id &&
    prev.model === next.model &&
    prev.reasoning_effort === next.reasoning_effort &&
    prev.reasoning_budget === next.reasoning_budget &&
    prev.prompt === next.prompt &&
    prev.output_schema === next.output_schema
  );
}

// Helper function to compare string arrays
function areStringArraysEqual(prev: string[], next: string[]): boolean {
  if (prev === next) return true;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i] !== next[i]) return false;
  }
  return true;
}

// Helper function to compare Version arrays
function areVersionArraysEqual(prev?: Version[], next?: Version[]): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (!areVersionsEqual(prev[i], next[i])) return false;
  }
  return true;
}

// Helper function to compare Message arrays
function areMessageArraysEqual(prev?: Message[], next?: Message[]): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i].role !== next[i].role || prev[i].content !== next[i].content) {
      return false;
    }
  }
  return true;
}

// Helper function to compare priceAndLatency objects
function arePriceAndLatencyEqual(
  prev?: VersionHeaderProps["priceAndLatency"],
  next?: VersionHeaderProps["priceAndLatency"]
): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;

  return (
    prev.avgCost === next.avgCost &&
    prev.avgDuration === next.avgDuration &&
    prev.allCosts === next.allCosts &&
    prev.allDurations === next.allDurations &&
    prev.versionCosts === next.versionCosts &&
    prev.versionDurations === next.versionDurations
  );
}

// Helper function to compare metrics arrays
function areMetricsEqual(
  prev?: { key: string; average: number }[],
  next?: { key: string; average: number }[]
): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i].key !== next[i].key || prev[i].average !== next[i].average) {
      return false;
    }
  }
  return true;
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

export default memo(VersionHeader, (prevProps, nextProps) => {
  return (
    areVersionsEqual(prevProps.version, nextProps.version) &&
    areStringArraysEqual(prevProps.optionalKeysToShow, nextProps.optionalKeysToShow) &&
    prevProps.index === nextProps.index &&
    arePriceAndLatencyEqual(prevProps.priceAndLatency, nextProps.priceAndLatency) &&
    areVersionArraysEqual(prevProps.versions, nextProps.versions) &&
    areMessageArraysEqual(prevProps.sharedPartsOfPrompts, nextProps.sharedPartsOfPrompts) &&
    areStringArraysEqual(prevProps.sharedKeypathsOfSchemas || [], nextProps.sharedKeypathsOfSchemas || []) &&
    prevProps.experimentId === nextProps.experimentId &&
    prevProps.completionId === nextProps.completionId &&
    prevProps.showAvgPrefix === nextProps.showAvgPrefix &&
    prevProps.agentId === nextProps.agentId &&
    prevProps.dragIndex === nextProps.dragIndex &&
    areAnnotationsEqual(prevProps.annotations, nextProps.annotations) &&
    areMetricsEqual(prevProps.metrics, nextProps.metrics)
    // Note: onReorderColumns, allMetricsPerKey, and experiment are not compared as they should be stable or are complex objects
  );
});
