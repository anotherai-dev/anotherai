import { useCallback, useMemo } from "react";
import { useLocalStorage } from "usehooks-ts";
import { Version } from "@/types/models";

/**
 * A hook for managing hidden versions in experiments with localStorage persistence
 */
export function useVersionHiding(experimentId: string) {
  const [hiddenVersionIds, setHiddenVersionIds] = useLocalStorage<string[]>(`hidden-versions-${experimentId}`, []);

  // Function to hide a version
  const hideVersion = useCallback(
    (versionId: string) => {
      setHiddenVersionIds((prev) => {
        if (!prev.includes(versionId)) {
          return [...prev, versionId];
        }
        return prev;
      });
    },
    [setHiddenVersionIds]
  );

  // Function to show a specific version
  const showVersion = useCallback(
    (versionId: string) => {
      setHiddenVersionIds((prev) => prev.filter((id) => id !== versionId));
    },
    [setHiddenVersionIds]
  );

  // Function to show all hidden versions
  const showAllHiddenVersions = useCallback(() => {
    setHiddenVersionIds([]);
  }, [setHiddenVersionIds]);

  // Function to check if a version is hidden
  const isVersionHidden = useCallback(
    (versionId: string) => {
      return hiddenVersionIds.includes(versionId);
    },
    [hiddenVersionIds]
  );

  // Function to filter out hidden versions from a versions array
  const getVisibleVersions = useCallback(
    <T extends { id: string }>(versions: T[]): T[] => {
      return versions.filter((version) => !hiddenVersionIds.includes(version.id));
    },
    [hiddenVersionIds]
  );

  // Function to get the count of hidden versions from a given versions array
  const getHiddenVersionCount = useCallback(
    (versions: Version[]) => {
      return versions.filter((version) => hiddenVersionIds.includes(version.id)).length;
    },
    [hiddenVersionIds]
  );

  // Memoized state for easy access
  const state = useMemo(
    () => ({
      hiddenVersionIds,
      hiddenCount: hiddenVersionIds.length,
      hasHiddenVersions: hiddenVersionIds.length > 0,
    }),
    [hiddenVersionIds]
  );

  return {
    ...state,
    hideVersion,
    showVersion,
    showAllHiddenVersions,
    isVersionHidden,
    getVisibleVersions,
    getHiddenVersionCount,
  };
}
