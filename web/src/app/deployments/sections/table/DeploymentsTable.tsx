"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { ActivityIndicator } from "@/components/ActivityIndicator";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageError } from "@/components/PageError";
import { Pagination } from "@/components/Pagination";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { formatDate, formatTotalCost } from "@/components/utils/utils";
import { Deployment } from "@/types/models";
import { DeploymentsBaseCell } from "./DeploymentsBaseCell";

// Column key constants
export const DEPLOYMENTS_COLUMNS = {
  AGENT_ID: "Agent Id",
  NAME: "Deployment Id",
  RUNS_LAST_7_DAYS: "Runs (Last 7d)",
  TOTAL_COST: "Total Cost (Last 7d)",
  CREATED_AT: "Created at",
  UPDATED_AT: "Updated at",
  CREATED_BY: "Created by",
} as const;

interface DeploymentStats {
  completions_last_7_days: number;
  completions_last_3_days: number;
  total_cost: number;
  active: boolean;
  last_completion_date: string | null;
}

interface DeploymentsTableProps {
  deployments: Deployment[];
  deploymentStats?: Map<string, DeploymentStats>;
  total: number;
  currentPage: number;
  pageSize: number;
  isLoading: boolean;
  error?: Error;
  onPageChange: (page: number) => void;
}

export function DeploymentsTable(props: DeploymentsTableProps) {
  const { deployments, deploymentStats, total, currentPage, pageSize, isLoading, error, onPageChange } = props;
  const router = useRouter();

  // Define display columns
  const columnHeaders = useMemo(() => {
    return [
      DEPLOYMENTS_COLUMNS.AGENT_ID,
      DEPLOYMENTS_COLUMNS.NAME,
      DEPLOYMENTS_COLUMNS.CREATED_BY,
      DEPLOYMENTS_COLUMNS.RUNS_LAST_7_DAYS,
      DEPLOYMENTS_COLUMNS.TOTAL_COST,
      DEPLOYMENTS_COLUMNS.CREATED_AT,
      DEPLOYMENTS_COLUMNS.UPDATED_AT,
    ];
  }, []);

  // Convert deployments to data (2D array for SimpleTableComponent)
  const data = useMemo(() => {
    return deployments.map((deployment) => {
      const stats = deploymentStats?.get(deployment.id);

      return [
        <DeploymentsBaseCell key="agent_id" className="text-gray-900">
          {deployment.agent_id}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="name" className="font-bold text-gray-900">
          <div className="flex items-baseline gap-2 min-w-0 break-words">
            {stats?.completions_last_3_days !== undefined && (
              <div className="flex items-center h-[1em] -translate-y-px">
                <ActivityIndicator completionsLast3Days={stats.completions_last_3_days} />
              </div>
            )}
            <span className="flex-1 truncate">{deployment.id}</span>
          </div>
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="created_by" className="text-gray-500">
          {deployment.created_by}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="runs" className="text-gray-500">
          {stats?.completions_last_7_days ?? 0}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="cost" className="text-gray-900">
          {formatTotalCost(stats?.total_cost)}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="created_at" className="text-gray-500 w-20">
          {formatDate(deployment.created_at, "relative_with_time")}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="updated_at" className="text-gray-500 w-20">
          {deployment.updated_at ? formatDate(deployment.updated_at, "relative_with_time") : "—"}
        </DeploymentsBaseCell>,
      ];
    });
  }, [deployments, deploymentStats]);

  // Handle click on row
  const handleRowClick = (index: number) => {
    const deployment = deployments[index];
    // URL encode the deployment ID to handle special characters like : and #
    // e.g., "politician-qa:production#1" becomes "politician-qa%3Aproduction%231"
    router.push(`/deployments/${encodeURIComponent(deployment.id)}`);
  };

  // Loading state
  if (isLoading) {
    return <LoadingState />;
  }

  // Error state
  if (error) {
    return <PageError error={error.message} />;
  }

  // Empty state
  if (deployments.length === 0) {
    return (
      <EmptyState
        title="No deployments found"
        subtitle="Create your first deployment to get started"
        documentationUrl="https://docs.anotherai.dev/deployments"
      />
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <SimpleTableComponent
        columnHeaders={columnHeaders}
        data={data}
        onRowClick={handleRowClick}
        minCellWidth={120}
        cellVerticalAlign="middle"
        columnWidths={["auto", "auto", "120px", "140px", "180px"]}
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
