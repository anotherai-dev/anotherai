import { useCallback, useMemo, useState } from "react";
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
import { getAllMetricsPerKey, getAllMetricsPerKeyForRow, getMetricsPerVersion } from "../../utils";
import { InputHeaderCell } from "./InputHeaderCell";
import { CompletionCell } from "./completion/CompletionCell";
import { VersionHeader } from "./version/VersionHeader";

type Props = {
  experiment: ExperimentWithLookups;
  annotations?: Annotation[]; // Add annotations prop
};

export function MatrixSection(props: Props) {
  const { experiment, annotations } = props;

  // State for column order - initially ordered by version index
  const [columnOrder, setColumnOrder] = useState<string[]>(() => experiment.versions.map((version) => version.id));

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
      .map((versionId) => experiment.versions.find((v) => v.id === versionId))
      .filter(Boolean) as typeof experiment.versions;
  }, [columnOrder, experiment]);

  const completionsPerVersion = useMemo(() => {
    return getCompletionsPerVersion(experiment);
  }, [experiment]);

  const priceAndLatencyPerVersion = useMemo(() => {
    return getPriceAndLatencyPerVersion(completionsPerVersion);
  }, [completionsPerVersion]);

  const metricsPerVersion = useMemo(() => {
    return getMetricsPerVersion(experiment, annotations);
  }, [experiment, annotations]);

  const allMetricsPerKey = useMemo(() => {
    return getAllMetricsPerKey(metricsPerVersion);
  }, [metricsPerVersion]);

  const optionalKeysToShow = useMemo(() => {
    return getDifferingVersionKeys(orderedVersions);
  }, [orderedVersions]);

  const sharedPartsOfPrompts = useMemo(() => {
    return getSharedPartsOfPrompts(orderedVersions);
  }, [orderedVersions]);

  const sharedKeypathsOfSchemas = useMemo(() => {
    return getSharedKeypathsOfSchemas(orderedVersions);
  }, [orderedVersions]);

  const stickyHeaderData = useMemo(() => {
    return orderedVersions.map((version) => {
      const originalIndex = experiment.versions.findIndex((v) => v.id === version.id);
      return {
        versionNumber: originalIndex + 1,
        modelId: version.model,
        reasoningEffort: version.reasoning_effort,
        reasoningBudget: version.reasoning_budget,
      };
    });
  }, [orderedVersions, experiment.versions]);

  const tableData = useMemo(() => {
    // Get arrays of average metrics per version for badge coloring
    const allAvgCosts = priceAndLatencyPerVersion.map(({ metrics }) => metrics.avgCost);
    const allAvgDurations = priceAndLatencyPerVersion.map(({ metrics }) => metrics.avgDuration);

    // Column headers with version info
    const columnHeaders = orderedVersions.map((version, dragIndex) => {
      const priceAndLatency = priceAndLatencyPerVersion.find(({ versionId }) => versionId === version.id);
      const metrics = metricsPerVersion?.[version.id];
      // Find the original index of this version in the original experiment.versions array
      const originalIndex = experiment.versions.findIndex((v) => v.id === version.id);
      return (
        <VersionHeader
          key={version.id}
          version={version}
          optionalKeysToShow={optionalKeysToShow}
          index={originalIndex}
          priceAndLatency={
            priceAndLatency?.metrics
              ? {
                  avgCost: priceAndLatency.metrics.avgCost,
                  avgDuration: priceAndLatency.metrics.avgDuration,
                  allCosts: allAvgCosts,
                  allDurations: allAvgDurations,
                  versionCosts: priceAndLatency.metrics.costs,
                  versionDurations: priceAndLatency.metrics.durations,
                }
              : undefined
          }
          versions={orderedVersions}
          sharedPartsOfPrompts={sharedPartsOfPrompts}
          sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
          annotations={annotations}
          experimentId={experiment.id}
          metrics={metrics}
          allMetricsPerKey={allMetricsPerKey}
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
    priceAndLatencyPerVersion,
    experiment,
    orderedVersions,
    optionalKeysToShow,
    sharedPartsOfPrompts,
    sharedKeypathsOfSchemas,
    annotations,
    metricsPerVersion,
    allMetricsPerKey,
    reorderColumns,
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
