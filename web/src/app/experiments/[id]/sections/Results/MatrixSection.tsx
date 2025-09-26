import { useCallback, useEffect, useMemo, useState } from "react";
import { TableComponent } from "@/components/TableComponent";
import {
  findCompletionForInputAndVersion,
  getCompletionsPerVersion,
  getDifferingVersionKeys,
  getPriceAndLatencyPerVersion,
  getSharedKeypathsOfSchemas,
  getSharedPartsOfPrompts,
} from "@/components/utils/utils";
import { Annotation, ExperimentWithLookups } from "@/types/models";
import {
  getAllMetricsPerKey,
  getAllMetricsPerKeyForRow,
  getAveragedMetricsPerVersion,
  getRawMetricsForSingleVersion,
  getRawMetricsPerVersionPerKey,
  sortVersionsByPromptAndSchema,
} from "../../utils";
import InputHeaderCell from "./InputHeaderCell";
import CompletionCell from "./completion/CompletionCell";
import VersionHeader from "./version/VersionHeader";

type Props = {
  experiment: ExperimentWithLookups;
  annotations?: Annotation[]; // Add annotations prop
};

export function MatrixSection(props: Props) {
  const { experiment, annotations } = props;

  // Sort versions to show ones with prompt or output schema first
  const sortedVersions = useMemo(() => {
    return sortVersionsByPromptAndSchema(experiment.versions);
  }, [experiment.versions]);

  // State for column order - initially ordered by sorted version index
  const [columnOrder, setColumnOrder] = useState<string[]>([]);

  // Update column order when sorted versions change
  useEffect(() => {
    setColumnOrder(sortedVersions.map((version) => version.id));
  }, [sortedVersions]);

  // Function to reorder columns
  const reorderColumns = useCallback(
    (fromIndex: number, toIndex: number) => {
      const newOrder = [...columnOrder];
      const [movedItem] = newOrder.splice(fromIndex, 1);
      newOrder.splice(toIndex, 0, movedItem);
      setColumnOrder(newOrder);
    },
    [columnOrder]
  );

  // Get versions in the current column order
  const orderedVersions = useMemo(() => {
    return columnOrder
      .map((versionId) => sortedVersions.find((v) => v.id === versionId))
      .filter(Boolean) as typeof sortedVersions;
  }, [columnOrder, sortedVersions]);

  const { averagedMetricsPerVersion, allMetricsPerKey } = useMemo(() => {
    const averagedMetrics = getAveragedMetricsPerVersion(experiment, annotations);
    const allMetrics = getAllMetricsPerKey(averagedMetrics);

    return {
      averagedMetricsPerVersion: averagedMetrics,
      allMetricsPerKey: allMetrics,
    };
  }, [experiment, annotations]);

  const stickyHeaderData = useMemo(() => {
    return orderedVersions.map((version) => {
      const originalIndex = sortedVersions.findIndex((v) => v.id === version.id);
      return {
        versionNumber: originalIndex + 1,
        modelId: version.model,
        reasoningEffort: version.reasoning_effort,
        reasoningBudget: version.reasoning_budget,
      };
    });
  }, [orderedVersions, sortedVersions]);

  const tableData = useMemo(() => {
    // Calculate values that are only used within this tableData
    const optionalKeysToShow = getDifferingVersionKeys(orderedVersions);
    const sharedPartsOfPrompts = getSharedPartsOfPrompts(orderedVersions);
    const sharedKeypathsOfSchemas = getSharedKeypathsOfSchemas(orderedVersions);
    const completionsPerVersion = getCompletionsPerVersion(experiment);
    const priceAndLatencyPerVersion = getPriceAndLatencyPerVersion(completionsPerVersion);
    // Get arrays of average metrics per version for badge coloring
    const allAvgCosts = priceAndLatencyPerVersion.map(({ metrics }) => metrics.avgCost);
    const allAvgDurations = priceAndLatencyPerVersion.map(({ metrics }) => metrics.avgDuration);

    // Calculate raw metrics lookup for percentile data
    const rawMetricsPerVersionPerKey = getRawMetricsPerVersionPerKey(experiment, annotations);
    const rawMetricsLookupByVersion: Record<string, Record<string, number[]> | undefined> = {};
    orderedVersions.forEach((version) => {
      rawMetricsLookupByVersion[version.id] = getRawMetricsForSingleVersion(rawMetricsPerVersionPerKey, version.id);
    });

    // Column headers with version info
    const columnHeaders = orderedVersions.map((version, dragIndex) => {
      const priceAndLatency = priceAndLatencyPerVersion.find(({ versionId }) => versionId === version.id);
      const metrics = averagedMetricsPerVersion?.[version.id] || [];
      const rawMetricsForVersion = rawMetricsLookupByVersion[version.id] || {};

      // Combine regular metrics with price and latency metrics
      const allMetrics = [...metrics];
      if (priceAndLatency?.metrics) {
        allMetrics.unshift(
          { key: "cost", average: priceAndLatency.metrics.avgCost },
          { key: "duration", average: priceAndLatency.metrics.avgDuration }
        );
      }

      // Combine allMetricsPerKey with price and latency data
      const allMetricsPerKeyForVersion = { ...allMetricsPerKey };
      if (priceAndLatency?.metrics) {
        allMetricsPerKeyForVersion.cost = allAvgCosts;
        allMetricsPerKeyForVersion.duration = allAvgDurations;
      }

      // Combine rawMetricsPerKey with price and latency data
      const versionMetricsPerKeyForVersion = { ...rawMetricsForVersion };
      if (priceAndLatency?.metrics) {
        versionMetricsPerKeyForVersion.cost = priceAndLatency.metrics.costs;
        versionMetricsPerKeyForVersion.duration = priceAndLatency.metrics.durations;
      }

      // Find the original index of this version in the sorted versions array
      const originalIndex = sortedVersions.findIndex((v) => v.id === version.id);
      return (
        <VersionHeader
          key={version.id}
          version={version}
          optionalKeysToShow={optionalKeysToShow}
          index={originalIndex}
          versions={orderedVersions}
          sharedPartsOfPrompts={sharedPartsOfPrompts}
          sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
          annotations={annotations}
          experimentId={experiment.id}
          metrics={allMetrics}
          allMetricsPerKey={allMetricsPerKeyForVersion}
          versionMetricsPerKey={versionMetricsPerKeyForVersion}
          agentId={experiment.agent_id}
          experiment={experiment}
          onReorderColumns={reorderColumns}
          dragIndex={dragIndex}
        />
      );
    });

    // Row headers with input info
    const rowHeaders =
      experiment.inputs?.map((input, index) => <InputHeaderCell key={input.id} input={input} index={index} />) || [];

    // Data cells showing completions
    const data =
      experiment.inputs?.map((input) => {
        // Get all completions for this input (row) to calculate comparison arrays
        const completionsForInput = orderedVersions
          .map((version) => findCompletionForInputAndVersion(experiment.completions || [], input.id, version.id))
          .filter(Boolean); // Remove undefined completions

        // Calculate cost and duration arrays for this row
        const allCostsForRow = completionsForInput.map((completion) => completion!.cost_usd || 0);
        const allDurationsForRow = completionsForInput.map((completion) => completion!.duration_seconds || 0);

        // Calculate metrics per key for this row (for row-based comparison coloring)
        const allMetricsPerKeyForRow = getAllMetricsPerKeyForRow(experiment, annotations, input.id);

        return orderedVersions.map((version) => {
          const completion = findCompletionForInputAndVersion(experiment.completions || [], input.id, version.id);

          return (
            <CompletionCell
              key={`${input.id}-${version.id}`}
              completion={completion}
              allCosts={allCostsForRow}
              allDurations={allDurationsForRow}
              annotations={annotations}
              experimentId={experiment.id}
              allMetricsPerKeyForRow={allMetricsPerKeyForRow}
              agentId={experiment.agent_id}
            />
          );
        });
      }) || [];

    return { columnHeaders, rowHeaders, data };
  }, [
    experiment,
    orderedVersions,
    annotations,
    averagedMetricsPerVersion,
    allMetricsPerKey,
    reorderColumns,
    sortedVersions,
  ]);

  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Experiment outputs</h2>
      <TableComponent
        columnHeaders={tableData.columnHeaders}
        rowHeaders={tableData.rowHeaders}
        data={tableData.data}
        minColumnWidth={400}
        hideScrollbar={false}
        stickyHeaderData={stickyHeaderData}
      />
    </div>
  );
}
