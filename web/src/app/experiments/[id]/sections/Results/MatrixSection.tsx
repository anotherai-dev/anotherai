import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocalStorage } from "usehooks-ts";
import { TableComponent } from "@/components/TableComponent";
import {
  findCompletionForInputAndVersion,
  getCompletionsPerVersion,
  getDifferingVersionKeys,
  getPriceAndLatencyPerVersion,
  getSharedKeypathsOfSchemas,
  getSharedPartsOfPrompts,
  getValidCosts,
  getValidDurations,
} from "@/components/utils/utils";
import { useColumnWidths } from "@/hooks/useColumnWidths";
import { useVersionHiding } from "@/hooks/useVersionHiding";
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
    return sortVersionsByPromptAndSchema(experiment.versions ?? []);
  }, [experiment.versions]);

  // State for column order - initially ordered by sorted version index
  const [columnOrder, setColumnOrder] = useState<string[]>([]);

  // Version hiding hook
  const { hiddenVersionIds, hideVersion, showAllHiddenVersions, hasHiddenVersions } = useVersionHiding(experiment.id);

  // Column widths hook
  const visibleVersionIds = useMemo(() => {
    return columnOrder.filter((versionId) => !hiddenVersionIds.includes(versionId));
  }, [columnOrder, hiddenVersionIds]);

  const { setColumnWidth, widthsArray, hasCustomWidths } = useColumnWidths(experiment.id, visibleVersionIds, 400);

  // First column width management
  const [firstColumnWidth, setFirstColumnWidth] = useLocalStorage<number>(`first-column-width-${experiment.id}`, 240);

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

  // Get versions in the current column order, excluding hidden versions
  const orderedVersions = useMemo(() => {
    return columnOrder
      .filter((versionId) => !hiddenVersionIds.includes(versionId))
      .map((versionId) => sortedVersions.find((v) => v.id === versionId))
      .filter(Boolean) as typeof sortedVersions;
  }, [columnOrder, sortedVersions, hiddenVersionIds]);

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
    // Get arrays of average metrics per version for badge coloring (filter out undefined values)
    const allAvgCosts = priceAndLatencyPerVersion
      .map(({ metrics }) => metrics.avgCost)
      .filter((cost): cost is number => cost !== undefined);
    const allAvgDurations = priceAndLatencyPerVersion
      .map(({ metrics }) => metrics.avgDuration)
      .filter((duration): duration is number => duration !== undefined);

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
        // Only add cost metric if it has a valid value
        if (priceAndLatency.metrics.avgCost !== undefined) {
          allMetrics.unshift({ key: "cost", average: priceAndLatency.metrics.avgCost });
        }
        // Only add duration metric if it has a valid value
        if (priceAndLatency.metrics.avgDuration !== undefined) {
          allMetrics.unshift({ key: "duration", average: priceAndLatency.metrics.avgDuration });
        }
      }

      // Combine allMetricsPerKey with price and latency data
      const allMetricsPerKeyForVersion = { ...allMetricsPerKey };
      if (priceAndLatency?.metrics) {
        if (allAvgCosts.length > 0) {
          allMetricsPerKeyForVersion.cost = allAvgCosts;
        }
        if (allAvgDurations.length > 0) {
          allMetricsPerKeyForVersion.duration = allAvgDurations;
        }
      }

      // Combine rawMetricsPerKey with price and latency data
      const versionMetricsPerKeyForVersion = { ...rawMetricsForVersion };
      if (priceAndLatency?.metrics) {
        versionMetricsPerKeyForVersion.cost = priceAndLatency.metrics.costs;
        versionMetricsPerKeyForVersion.duration = priceAndLatency.metrics.durations;
      }

      // Find the original index of this version in the sorted versions array
      const originalIndex = sortedVersions.findIndex((v) => v.id === version.id);
      const nextVersionId = dragIndex < orderedVersions.length - 1 ? orderedVersions[dragIndex + 1]?.id : undefined;
      const isLastColumn = dragIndex === orderedVersions.length - 1;

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
          onHideVersion={hideVersion}
          columnWidth={widthsArray[dragIndex]}
          onColumnWidthChange={setColumnWidth}
          nextVersionId={nextVersionId}
          isLastColumn={isLastColumn}
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

        // Calculate cost and duration arrays for this row using centralized utility functions
        const allCostsForRow = getValidCosts(completionsForInput);
        const allDurationsForRow = getValidDurations(completionsForInput);

        // Calculate metrics per key for this row (for row-based comparison coloring)
        const allMetricsPerKeyForRowData = getAllMetricsPerKeyForRow(experiment, annotations, input.id);

        // Combine all metrics per key for this row
        const allMetricsPerKeyForRow: Record<string, number[]> = {
          ...allMetricsPerKeyForRowData,
        };

        // Add cost and duration arrays if they have data
        if (allCostsForRow.length > 0) {
          allMetricsPerKeyForRow.cost = allCostsForRow;
        }
        if (allDurationsForRow.length > 0) {
          allMetricsPerKeyForRow.duration = allDurationsForRow;
        }

        return orderedVersions.map((version) => {
          const completion = findCompletionForInputAndVersion(experiment.completions || [], input.id, version.id);

          return (
            <CompletionCell
              key={`${input.id}-${version.id}`}
              completion={completion}
              annotations={annotations}
              experimentId={experiment.id}
              allMetricsPerKey={allMetricsPerKeyForRow}
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
    hideVersion,
    setColumnWidth,
    widthsArray,
  ]);

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Experiment outputs</h2>
        {hasHiddenVersions && (
          <button
            onClick={showAllHiddenVersions}
            className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] h-8 flex items-center justify-center shadow-sm shadow-black/5"
            title={`Show ${hiddenVersionIds.length} hidden version${hiddenVersionIds.length === 1 ? "" : "s"}`}
          >
            <span className="text-xs font-medium">
              Show {hiddenVersionIds.length} hidden version{hiddenVersionIds.length === 1 ? "" : "s"}
            </span>
          </button>
        )}
      </div>
      {experiment.versions && experiment.versions.length > 0 ? (
        <TableComponent
          columnHeaders={tableData.columnHeaders}
          rowHeaders={tableData.rowHeaders}
          data={tableData.data}
          minColumnWidth={400}
          hideScrollbar={false}
          stickyHeaderData={stickyHeaderData}
          columnWidths={
            !hasCustomWidths
              ? undefined // Let TableComponent auto-size using available space
              : widthsArray
          }
          firstColumnWidth={firstColumnWidth}
          onFirstColumnWidthChange={setFirstColumnWidth}
        />
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-[10px]">
          <div className="px-4 py-2 text-sm text-gray-700">No versions found for this experiment</div>
        </div>
      )}
    </div>
  );
}
