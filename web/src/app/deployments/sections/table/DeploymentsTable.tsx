"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { PageError } from "@/components/PageError";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { formatRelativeDateWithTime, formatTotalCost } from "@/components/utils/utils";
import { Deployment } from "@/types/models";
import { DeploymentsBaseCell } from "./DeploymentsBaseCell";

// Column key constants
export const DEPLOYMENTS_COLUMNS = {
  AGENT_ID: "Agent Id",
  NAME: "Name",
  RUNS_LAST_7_DAYS: "Runs (Last 7d)",
  TOTAL_COST: "Total Cost (Last 7d)",
  CREATED_AT: "Created at",
} as const;

interface DeploymentStats {
  completions_last_7_days: number;
  total_cost: number;
  active: boolean;
  last_completion_date: string | null;
}

interface DeploymentsTableProps {
  deployments: Deployment[];
  deploymentStats?: Map<string, DeploymentStats>;
  isLoading: boolean;
  error?: Error;
}

export function DeploymentsTable(props: DeploymentsTableProps) {
  const { deployments, deploymentStats, isLoading, error } = props;
  const router = useRouter();

  // Define display columns
  const columnHeaders = useMemo(() => {
    return [
      DEPLOYMENTS_COLUMNS.AGENT_ID,
      DEPLOYMENTS_COLUMNS.NAME,
      DEPLOYMENTS_COLUMNS.RUNS_LAST_7_DAYS,
      DEPLOYMENTS_COLUMNS.TOTAL_COST,
      DEPLOYMENTS_COLUMNS.CREATED_AT,
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
          {deployment.id}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="runs" className="text-gray-500">
          {stats?.completions_last_7_days ?? 0}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="cost" className="text-gray-900">
          {formatTotalCost(stats?.total_cost)}
        </DeploymentsBaseCell>,
        <DeploymentsBaseCell key="created_at" className="text-gray-500">
          {formatRelativeDateWithTime(deployment.created_at)}
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
    return <LoadingIndicator />;
  }

  // Error state
  if (error) {
    return <PageError error={error.message} />;
  }

  // Empty state
  if (deployments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-500">
        <div className="text-lg font-medium mb-2">No deployments found</div>
        <div className="text-sm">Create your first deployment to get started</div>
      </div>
    );
  }

  return (
    <SimpleTableComponent
      columnHeaders={columnHeaders}
      data={data}
      onRowClick={handleRowClick}
      minCellWidth={120}
      cellVerticalAlign="middle"
      columnWidths={["auto", "auto", "120px", "140px", "180px"]}
    />
  );
}
