import { useMemo } from "react";
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
  getMetricsPerVersion,
} from "../../utils";
import { InputHeaderCell } from "./InputHeaderCell";
import { CompletionCell } from "./completion/CompletionCell";
import { VersionHeader } from "./version/VersionHeader";

type Props = {
  experiment: ExperimentWithLookups;
  annotations?: Annotation[]; // Add annotations prop
};

export function MatrixSection(props: Props) {
  const { experiment, annotations } = props;

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
    return getDifferingVersionKeys(experiment.versions);
  }, [experiment.versions]);

  const sharedPartsOfPrompts = useMemo(() => {
    return getSharedPartsOfPrompts(experiment.versions);
  }, [experiment.versions]);

  const sharedKeypathsOfSchemas = useMemo(() => {
    return getSharedKeypathsOfSchemas(experiment.versions);
  }, [experiment.versions]);

  const tableData = useMemo(() => {
    // Get arrays of average metrics per version for badge coloring
    const allAvgCosts = priceAndLatencyPerVersion.map(
      ({ metrics }) => metrics.avgCost
    );
    const allAvgDurations = priceAndLatencyPerVersion.map(
      ({ metrics }) => metrics.avgDuration
    );

    // Column headers with version info
    const columnHeaders = experiment.versions.map((version, index) => {
      const priceAndLatency = priceAndLatencyPerVersion.find(
        ({ versionId }) => versionId === version.id
      );
      const metrics = metricsPerVersion?.[version.id];
      return (
        <VersionHeader
          key={version.id}
          version={version}
          optionalKeysToShow={optionalKeysToShow}
          index={index}
          priceAndLatency={
            priceAndLatency?.metrics
              ? {
                  ...priceAndLatency.metrics,
                  allCosts: allAvgCosts,
                  allDurations: allAvgDurations,
                }
              : undefined
          }
          versions={experiment.versions}
          sharedPartsOfPrompts={sharedPartsOfPrompts}
          sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
          annotations={annotations}
          experimentId={experiment.id}
          metrics={metrics}
          allMetricsPerKey={allMetricsPerKey}
          agentId={experiment.agent_id}
        />
      );
    });

    // Row headers with input info
    const rowHeaders =
      experiment.inputs?.map((input, index) => (
        <InputHeaderCell key={input.id} input={input} index={index} />
      )) || [];

    // Data cells showing completions
    const data =
      experiment.inputs?.map((input) => {
        // Get all completions for this input (row) to calculate comparison arrays
        const completionsForInput = experiment.versions
          .map((version) =>
            findCompletionForInputAndVersion(
              experiment.completions || [],
              input.id,
              version.id
            )
          )
          .filter(Boolean); // Remove undefined completions

        // Calculate cost and duration arrays for this row
        const allCostsForRow = completionsForInput.map(
          (completion) => completion!.cost_usd || 0
        );
        const allDurationsForRow = completionsForInput.map(
          (completion) => completion!.duration_seconds || 0
        );

        // Calculate metrics per key for this row (for row-based comparison coloring)
        const allMetricsPerKeyForRow = getAllMetricsPerKeyForRow(
          experiment,
          annotations,
          input.id
        );

        return experiment.versions.map((version) => {
          const completion = findCompletionForInputAndVersion(
            experiment.completions || [],
            input.id,
            version.id
          );

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
    optionalKeysToShow,
    sharedPartsOfPrompts,
    sharedKeypathsOfSchemas,
    annotations,
    metricsPerVersion,
    allMetricsPerKey,
  ]);

  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">
        Experiment outputs
      </h2>
      <TableComponent
        columnHeaders={tableData.columnHeaders}
        rowHeaders={tableData.rowHeaders}
        data={tableData.data}
        minColumnWidth={300}
      />
    </div>
  );
}
