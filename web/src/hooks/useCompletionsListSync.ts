import { useCallback, useEffect } from "react";
import { useStoredCompletions } from "@/store/stored_completions";

/**
 * Hook to sync completions data with the stored completions list for modal navigation
 * @param data - The completions data to store
 */
export function useCompletionsListSync(data: Record<string, unknown>[] | null | undefined) {
  const { setStoredCompletionsList, clearStoredCompletionsList } = useStoredCompletions();

  // Create stable callback
  const updateStoredCompletions = useCallback(
    (completions: Record<string, unknown>[]) => {
      setStoredCompletionsList(completions);
    },
    [setStoredCompletionsList]
  );

  // Update stored completions list when data changes
  useEffect(() => {
    if (data) {
      updateStoredCompletions(data);
    }
  }, [data, updateStoredCompletions]);

  // Clear stored completions list when component unmounts
  useEffect(() => {
    return () => {
      clearStoredCompletionsList();
    };
  }, [clearStoredCompletionsList]);
}
