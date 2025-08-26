"use client";

import { useMemo } from "react";
import { HeaderSection } from "@/components/HeaderSection";
import { useOrFetchMultipleDeploymentStats } from "@/store/deployment_stats";
import { useOrFetchDeployments } from "@/store/deployments";
import { DeploymentsTable } from "./sections/table/DeploymentsTable";

export default function DeploymentsPage() {
  const { deployments, isLoading, error } = useOrFetchDeployments();

  // Get deployment IDs for stats fetching
  const deploymentIds = useMemo(() => deployments.map((deployment) => deployment.id), [deployments]);

  // Fetch stats for all deployments
  const { allStats, isLoading: isLoadingStats } = useOrFetchMultipleDeploymentStats(deploymentIds);

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 gap-6 bg-gray-50">
      <HeaderSection
        title="Deployments"
        description="View and manage your AI agent deployments across different environments and configurations"
      />

      <DeploymentsTable
        deployments={deployments}
        deploymentStats={allStats}
        isLoading={isLoading || isLoadingStats}
        error={error ?? undefined}
      />
    </div>
  );
}
