import { useMemo } from "react";
import {
  getMatchingVersionKeys,
  getVersionWithDefaults,
  sortVersionKeys,
} from "@/components/utils/utils";
import { Annotation, ExperimentWithLookups } from "@/types/models";
import { MatchingRow } from "./MatchingRow";

type Props = {
  experiment: ExperimentWithLookups;
  annotations?: Annotation[];
  experimentId?: string;
  completionId?: string;
};

export function MatchingSection(props: Props) {
  const { experiment, annotations, experimentId, completionId } = props;

  const matchingContentKeys = useMemo(() => {
    const keys = getMatchingVersionKeys(experiment.versions);
    return sortVersionKeys(keys);
  }, [experiment.versions]);

  const versionWithDefaults = useMemo(() => {
    if (experiment.versions.length === 0) return null;
    return getVersionWithDefaults(experiment.versions[0]);
  }, [experiment.versions]);

  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
        Matching Content
      </h2>
      <div className="bg-gray-50 border border-gray-200 rounded-[10px]">
        {matchingContentKeys.length > 0 && versionWithDefaults ? (
          matchingContentKeys.map((key) => (
            <MatchingRow
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
          <div className="px-4 py-2 text-sm text-gray-700">
            No matching keys found across versions
          </div>
        )}
      </div>
    </div>
  );
}
