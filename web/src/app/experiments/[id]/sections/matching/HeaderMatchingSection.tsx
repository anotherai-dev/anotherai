import { ChevronDown, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import {
  IGNORED_VERSION_KEYS,
  getMatchingVersionKeys,
  getVersionWithDefaults,
  sortVersionKeys,
} from "@/components/utils/utils";
import { Annotation, ExperimentWithLookups } from "@/types/models";
import { HeaderMatchingRow } from "./HeaderMatchingRow";

type Props = {
  experiment?: ExperimentWithLookups;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
};

export function HeaderMatchingSection(props: Props) {
  const { experiment, annotations, experimentId, completionId } = props;
  const [isExpanded, setIsExpanded] = useState(false);

  const matchingContentKeys = useMemo(() => {
    if (!experiment?.versions || !Array.isArray(experiment.versions) || experiment.versions.length === 0) {
      return [];
    }
    const keys = getMatchingVersionKeys(experiment.versions, [...IGNORED_VERSION_KEYS, "model"]);
    return sortVersionKeys(keys);
  }, [experiment?.versions]);

  const versionWithDefaults = useMemo(() => {
    if (!experiment?.versions || !Array.isArray(experiment.versions) || experiment.versions.length === 0) {
      return null;
    }
    return getVersionWithDefaults(experiment.versions[0]);
  }, [experiment?.versions]);

  // Don't render anything if no experiment data
  if (!experiment?.versions || !Array.isArray(experiment.versions) || experiment.versions.length === 0) {
    return null;
  }

  return (
    <div className="">
      <div className="border border-gray-200 rounded-[2px]">
        {/* Header row with toggle */}
        <div
          className={`flex justify-between items-center px-[8px] py-2 cursor-pointer bg-gray-50 hover:bg-gray-100/50 ${isExpanded ? "border-b border-gray-200" : ""}`}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="text-xs font-medium text-gray-900">Similar Parameters</div>
          <div className="text-gray-500">{isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</div>
        </div>

        {/* Content rows - only show when expanded */}
        {isExpanded && (
          <div className="bg-gray-50/50">
            {matchingContentKeys.length > 0 && versionWithDefaults ? (
              matchingContentKeys.map((key) => (
                <HeaderMatchingRow
                  key={key}
                  keyName={key}
                  versionWithDefaults={versionWithDefaults}
                  annotations={annotations}
                  experimentId={experimentId}
                  completionId={completionId}
                  agentId={experiment.agent_id}
                />
              ))
            ) : (
              <div className="px-4 py-2 text-sm text-gray-700">No matching keys found across versions</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
