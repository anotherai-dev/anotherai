import { useMemo } from "react";
import { useCompletionsQuery } from "@/store/completions";
import { Completion } from "@/types/models";

/**
 * Hook to fetch completions that are part of the same trace as the given completion.
 * Looks for related completions based on conversation_id and trace_id metadata.
 */
export function useTraceCompletions(completion: Completion | undefined) {
  const traceQuery = useMemo(() => {
    if (!completion) return undefined;

    const queries: string[] = [];

    // Check for conversation_id in both column and metadata
    if (completion.conversation_id) {
      queries.push(`conversation_id = '${completion.conversation_id}'`);
    }
    if (completion.metadata?.conversation_id) {
      queries.push(`metadata['conversation_id'] = '${completion.metadata.conversation_id}'`);
    }

    // Check for trace_id in metadata
    if (completion.metadata?.trace_id) {
      queries.push(`metadata['trace_id'] = '${completion.metadata.trace_id}'`);
    }

    if (queries.length === 0) {
      return undefined; // No trace identifiers found
    }

    // Build query to fetch related completions
    const whereClause = queries.join(" OR ");
    return `SELECT * FROM completions WHERE ${whereClause} ORDER BY created_at ASC`;
  }, [completion]);

  const { data: traceData, isLoading, error } = useCompletionsQuery(traceQuery);

  const traceCompletions = useMemo(() => {
    if (!traceData) return undefined;

    // Keep as raw data records
    return traceData;
  }, [traceData]);

  const groupedTraceCompletions = useMemo(() => {
    if (!traceCompletions) return undefined;

    const grouped: Record<string, Record<string, Record<string, unknown>[]>> = {};

    traceCompletions.forEach((tc) => {
      const agentId = tc.agent_id as string;
      const version = typeof tc.version === "string" ? JSON.parse(tc.version) : tc.version;
      const modelId = (version?.model as string) || "unknown";

      if (!grouped[agentId]) {
        grouped[agentId] = {};
      }
      if (!grouped[agentId][modelId]) {
        grouped[agentId][modelId] = [];
      }

      grouped[agentId][modelId].push(tc);
    });

    return grouped;
  }, [traceCompletions]);

  const currentIndex = useMemo(() => {
    if (!traceCompletions || !completion) return -1;

    return traceCompletions.findIndex((tc) => tc.id === completion.id);
  }, [traceCompletions, completion]);

  const hasTrace = traceCompletions && traceCompletions.length > 1;

  return {
    traceCompletions,
    groupedTraceCompletions,
    isLoading,
    error,
    hasTrace,
    currentIndex,
    totalCount: traceCompletions?.length || 0,
  };
}
