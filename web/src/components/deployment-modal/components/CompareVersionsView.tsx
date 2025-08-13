import { ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import {
  getMatchingVersionKeys,
  getSharedKeypathsOfSchemas,
  getSharedPartsOfPrompts,
  getVersionKeys,
  getVersionWithDefaults,
  sortVersionKeys,
} from "@/components/utils/utils";
import { Version } from "@/types/models";
import { CompareSection } from "./CompareSection";

interface CompareVersionsViewProps {
  versionCurrentlyDeployed?: Version;
  versionToBeDeployed?: Version;
}

export function CompareVersionsView({
  versionCurrentlyDeployed,
  versionToBeDeployed,
}: CompareVersionsViewProps) {
  const [isUnchangedExpanded, setIsUnchangedExpanded] = useState(false);
  const [isDiffMode, setIsDiffMode] = useState(true);
  // Calculate shared parts for diff highlighting
  const sharedPartsOfPrompts = useMemo(() => {
    if (!versionCurrentlyDeployed || !versionToBeDeployed) return undefined;
    return getSharedPartsOfPrompts([
      versionCurrentlyDeployed,
      versionToBeDeployed,
    ]);
  }, [versionCurrentlyDeployed, versionToBeDeployed]);

  const sharedKeypathsOfSchemas = useMemo(() => {
    if (!versionCurrentlyDeployed || !versionToBeDeployed) return undefined;
    return getSharedKeypathsOfSchemas([
      versionCurrentlyDeployed,
      versionToBeDeployed,
    ]);
  }, [versionCurrentlyDeployed, versionToBeDeployed]);

  // Use the same logic as MatchingSection to get all version keys and defaults
  const { changedKeys, unchangedKeys, currentWithDefaults, newWithDefaults } =
    useMemo(() => {
      // Create versions array to use getMatchingVersionKeys (same as MatchingSection)
      const versions = [];
      if (versionCurrentlyDeployed) versions.push(versionCurrentlyDeployed);
      if (versionToBeDeployed) versions.push(versionToBeDeployed);

      // If we only have one version, add it twice so getMatchingVersionKeys works properly
      if (versions.length === 1) {
        versions.push(versions[0]);
      }

      // Get all keys and matching keys
      const allKeys = versions.length > 0 ? getVersionKeys(versions) : [];
      const matchingKeys =
        versions.length > 0 ? getMatchingVersionKeys(versions) : [];

      // Get unmatching keys by removing matching ones from all keys
      const unmatchingKeys = allKeys.filter(
        (key) => !matchingKeys.includes(key)
      );
      const sortedUnmatchingKeys = sortVersionKeys(unmatchingKeys);

      // Apply defaults to both versions
      const currentDefaults = versionCurrentlyDeployed
        ? getVersionWithDefaults(versionCurrentlyDeployed)
        : undefined;
      const newDefaults = versionToBeDeployed
        ? getVersionWithDefaults(versionToBeDeployed)
        : undefined;

      // Changed keys are the unmatching keys (values are different)
      const changed = sortedUnmatchingKeys;
      // Unchanged keys are the matching keys (values are the same)
      const unchanged = sortVersionKeys(matchingKeys);

      return {
        changedKeys: changed,
        unchangedKeys: unchanged,
        currentWithDefaults: currentDefaults,
        newWithDefaults: newDefaults,
      };
    }, [versionCurrentlyDeployed, versionToBeDeployed]);

  return (
    <div className="flex flex-col h-full p-6 overflow-y-auto">
      {changedKeys.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-base font-bold text-gray-900">Changed</h2>
            <div className="flex items-center gap-2">
              <span className="text-[12px] text-gray-700">Diff Mode</span>
              <button
                onClick={() => setIsDiffMode(!isDiffMode)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isDiffMode ? "bg-black" : "bg-gray-200"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isDiffMode ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </div>
          <CompareSection
            keys={changedKeys}
            currentWithDefaults={currentWithDefaults}
            newWithDefaults={newWithDefaults}
            isDiffMode={isDiffMode}
            sharedPartsOfPrompts={sharedPartsOfPrompts}
            sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
          />
        </div>
      )}

      {unchangedKeys.length > 0 && (
        <div className="mb-6">
          <button
            onClick={() => setIsUnchangedExpanded(!isUnchangedExpanded)}
            className="flex items-center gap-1 text-base font-bold text-gray-900 mb-2 hover:text-gray-700 transition-colors cursor-pointer"
          >
            <span>Unchanged</span>
            <ChevronRight
              className={`w-4.5 h-4.5 transition-transform text-gray-500 ${isUnchangedExpanded ? "rotate-90" : ""}`}
            />
          </button>
          {isUnchangedExpanded && (
            <CompareSection
              keys={unchangedKeys}
              currentWithDefaults={currentWithDefaults}
              newWithDefaults={newWithDefaults}
            />
          )}
        </div>
      )}
    </div>
  );
}
