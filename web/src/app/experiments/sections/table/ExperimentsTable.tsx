"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageError } from "@/components/PageError";
import { Pagination } from "@/components/Pagination";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { formatRelativeDate } from "@/components/utils/utils";
import { ExperimentListItem } from "@/types/models";
import { ExperimentsBaseCell } from "./ExperimentsBaseCell";
import { ExperimentsTableExperimentCell } from "./ExperimentsTableExperimentCell";

// Column key constants
export const EXPERIMENTS_COLUMNS = {
  EXPERIMENT: "Experiment",
  AGENT_ID: "Agent ID",
  CREATED_AT: "Created at",
  AUTHOR: "Author",
} as const;

interface ExperimentsTableProps {
  experiments: ExperimentListItem[];
  total: number;
  currentPage: number;
  pageSize: number;
  isLoading: boolean;
  error?: Error | null;
  onPageChange: (page: number) => void;
}

export function ExperimentsTable(props: ExperimentsTableProps) {
  const { experiments, total, currentPage, pageSize, isLoading, error, onPageChange } = props;
  const router = useRouter();

  // Define display columns
  const columnHeaders = useMemo(() => {
    return [
      EXPERIMENTS_COLUMNS.EXPERIMENT,
      EXPERIMENTS_COLUMNS.AGENT_ID,
      EXPERIMENTS_COLUMNS.AUTHOR,
      EXPERIMENTS_COLUMNS.CREATED_AT,
    ];
  }, []);

  // Transform experiment data for display
  const displayData = useMemo(() => {
    return experiments.map((experiment) => ({
      [EXPERIMENTS_COLUMNS.EXPERIMENT]: {
        title: experiment.title || experiment.id,
        description: experiment.description,
        result: experiment.result,
      },
      [EXPERIMENTS_COLUMNS.AGENT_ID]: experiment.agent_id,
      [EXPERIMENTS_COLUMNS.AUTHOR]: experiment.author_name,
      [EXPERIMENTS_COLUMNS.CREATED_AT]: experiment.created_at,
      _originalExperiment: experiment,
    }));
  }, [experiments]);

  const handleRowClick = (rowIndex: number) => {
    const displayRow = displayData[rowIndex];
    const experiment = displayRow._originalExperiment;
    const experimentId = experiment.id;

    if (!experimentId) {
      return;
    }

    router.push(`/experiments/${encodeURIComponent(experimentId)}`, {
      scroll: false,
    });
  };

  if (error) {
    return <PageError error={error.message} />;
  }

  if (isLoading) {
    return <LoadingState />;
  }

  if (!isLoading && displayData.length === 0) {
    return (
      <EmptyState
        title="No experiments found."
        subtitle="Create your first experiment to get started"
        documentationUrl="https://docs.anotherai.dev/experiments"
      />
    );
  }

  if (displayData.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <SimpleTableComponent
        columnHeaders={columnHeaders}
        data={displayData.map((row) =>
          columnHeaders.map((header) => {
            const value = row[header as keyof typeof row];

            switch (header) {
              case EXPERIMENTS_COLUMNS.EXPERIMENT:
                return (
                  <ExperimentsTableExperimentCell
                    key={header}
                    value={
                      value as {
                        title: string;
                        description: string;
                        result?: string;
                      }
                    }
                  />
                );

              case EXPERIMENTS_COLUMNS.AGENT_ID:
                return <ExperimentsBaseCell key={header} value={value} />;

              case EXPERIMENTS_COLUMNS.AUTHOR:
                return <ExperimentsBaseCell key={header} value={value} />;

              case EXPERIMENTS_COLUMNS.CREATED_AT:
                return <ExperimentsBaseCell key={header} value={value} formatter={formatRelativeDate} />;

              default:
                return <ExperimentsBaseCell key={header} value={value} />;
            }
          })
        )}
        minCellWidth={120}
        onRowClick={handleRowClick}
        cellVerticalAlign="middle"
        columnWidths={["auto", "230px", "120px", "160px"]}
        className="border-0 rounded-none"
      />

      <Pagination
        currentPage={currentPage}
        totalItems={total}
        pageSize={pageSize}
        onPageChange={onPageChange}
        isLoading={isLoading}
      />
    </div>
  );
}
