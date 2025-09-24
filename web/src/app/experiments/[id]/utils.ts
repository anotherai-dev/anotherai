import { getCompletionsPerVersion } from "@/components/utils/utils";
import { Annotation, ExperimentCompletion, ExperimentWithLookups, Version } from "@/types/models";

/**
 * Sorts versions to prioritize those with prompt or output schema first.
 *
 * @param versions - Array of versions to sort
 * @returns Array of versions with prompt/schema versions first, maintaining original order within each group
 */
export function sortVersionsByPromptAndSchema(versions: Version[]): Version[] {
  return [...versions].sort((a, b) => {
    const aHasPromptOrSchema = Boolean(a.prompt || a.output_schema);
    const bHasPromptOrSchema = Boolean(b.prompt || b.output_schema);

    // If one has prompt/schema and the other doesn't, prioritize the one that has it
    if (aHasPromptOrSchema && !bHasPromptOrSchema) return -1;
    if (!aHasPromptOrSchema && bHasPromptOrSchema) return 1;

    // If both have or both don't have, maintain original order
    return 0;
  });
}

/**
 * Finds all unique metric keys and their average values from a collection of annotations.
 *
 * @param annotations - Array of annotations to extract metrics from
 * @returns Array of objects with key and average value for each metric type
 */
export function findAllMetricKeysAndAverages(annotations: Annotation[]): Array<{ key: string; average: number }> {
  const metricsMap = new Map<string, number[]>();

  // Collect all values for each metric key
  annotations.forEach((annotation) => {
    if (annotation.metric?.name && typeof annotation.metric.value === "number") {
      const key = annotation.metric.name;
      const value = annotation.metric.value;

      if (metricsMap.has(key)) {
        metricsMap.get(key)!.push(value);
      } else {
        metricsMap.set(key, [value]);
      }
    }
  });

  // Calculate averages and return sorted results
  const results = Array.from(metricsMap.entries()).map(([key, values]) => ({
    key,
    average: parseFloat((values.reduce((sum, val) => sum + val, 0) / values.length).toFixed(2)),
  }));

  return results.sort((a, b) => a.key.localeCompare(b.key));
}

/**
 * Gets metrics per version by filtering annotations for completions of each version.
 *
 * @param experiment - The experiment with lookups containing completions and versions
 * @param annotations - Array of annotations to analyze (optional)
 * @returns Object where key is version ID and value is array of metric key/average pairs, or undefined if no annotations
 */
export function getMetricsPerVersion(
  experiment: ExperimentWithLookups,
  annotations?: Annotation[]
): Record<string, Array<{ key: string; average: number }>> | undefined {
  if (!annotations) {
    return undefined;
  }

  const metricsPerVersion: Record<string, Array<{ key: string; average: number }>> = {};

  // Use existing utility to get completions grouped by version
  const completionsPerVersion = getCompletionsPerVersion(experiment);

  completionsPerVersion.forEach(({ versionId, completions }) => {
    // Get completion IDs for this version
    const completionIds = completions.map((completion) => completion.id);

    // Filter annotations that belong to completions of this version
    const annotationsForVersion = annotations.filter(
      (annotation) => annotation.target?.completion_id && completionIds.includes(annotation.target.completion_id)
    );

    // Get metrics for this version using the existing function
    const metricsForVersion = findAllMetricKeysAndAverages(annotationsForVersion);

    metricsPerVersion[versionId] = metricsForVersion;
  });

  return metricsPerVersion;
}

/**
 * Extracts all metric values per key across all versions for comparison coloring.
 *
 * @param metricsPerVersion - Object mapping version ID to array of metrics
 * @returns Object mapping metric key to array of all values across versions
 */
export function getAllMetricsPerKey(
  metricsPerVersion: Record<string, Array<{ key: string; average: number }>> | undefined
): Record<string, number[]> | undefined {
  if (!metricsPerVersion) {
    return undefined;
  }

  const allMetricsPerKey: Record<string, number[]> = {};

  // Collect all metric keys first
  const allMetricKeys = new Set<string>();
  Object.values(metricsPerVersion).forEach((metrics) => {
    metrics.forEach((metric) => allMetricKeys.add(metric.key));
  });

  // For each metric key, collect all values across versions
  allMetricKeys.forEach((key) => {
    const valuesForKey: number[] = [];
    Object.values(metricsPerVersion).forEach((metrics) => {
      const metricForKey = metrics.find((m) => m.key === key);
      if (metricForKey) {
        valuesForKey.push(metricForKey.average);
      }
    });
    allMetricsPerKey[key] = valuesForKey;
  });

  return allMetricsPerKey;
}

/**
 * Gets metrics for a specific completion from annotations.
 *
 * @param annotations - Array of annotations to search through
 * @param completionId - ID of the completion to find metrics for
 * @returns Array of metric key/average pairs for the completion
 */
export function getMetricsForCompletion(
  annotations: Annotation[],
  completionId: string
): Array<{ key: string; average: number }> {
  // Filter annotations that target this specific completion
  const completionAnnotations = annotations.filter(
    (annotation) => annotation.target?.completion_id === completionId && annotation.metric
  );

  // Use the existing function to calculate metrics
  return findAllMetricKeysAndAverages(completionAnnotations);
}

/**
 * Gets all metrics per key for a specific row (input) across all versions.
 * This is used for row-based comparison coloring in completion cells.
 *
 * @param experiment - The experiment containing completions
 * @param annotations - Array of annotations (optional)
 * @param inputId - ID of the input (row) to analyze
 * @returns Object mapping metric key to array of values across versions for this row, or undefined if no annotations
 */
export function getAllMetricsPerKeyForRow(
  experiment: ExperimentWithLookups,
  annotations: Annotation[] | undefined,
  inputId: string
): Record<string, number[]> | undefined {
  if (!annotations) {
    return undefined;
  }

  const metricsPerKeyForRow: Record<string, number[]> = {};

  // Get all completions for this input across all versions
  const completionsForInput = experiment.versions
    .map((version) => {
      const completion = experiment.completions.find((c) => c.input.id === inputId && c.version.id === version.id);
      return completion;
    })
    .filter(Boolean) as ExperimentCompletion[];

  // For each completion, get its metrics and group by key
  completionsForInput.forEach((completion) => {
    const metricsForCompletion = getMetricsForCompletion(annotations, completion.id);

    metricsForCompletion.forEach(({ key, average }) => {
      if (!metricsPerKeyForRow[key]) {
        metricsPerKeyForRow[key] = [];
      }
      metricsPerKeyForRow[key].push(average);
    });
  });

  return metricsPerKeyForRow;
}
