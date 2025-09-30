"use client";

import { useMemo } from "react";
import { HeaderSection } from "@/components/HeaderSection";
import { useOrFetchMultipleDeploymentStats } from "@/store/deployment_stats";
import { useOrFetchDeployments } from "@/store/deployments";
import { DeploymentsTable } from "./sections/table/DeploymentsTable";

export default function DeploymentsPage() {
  const { deployments, isLoading, error, total, currentPage, pageSize, setPage } = useOrFetchDeployments();

  // Get deployment IDs for stats fetching
  const deploymentIds = useMemo(() => deployments.map((deployment) => deployment.id), [deployments]);

  // Fetch stats for all deployments
  const { allStats, isLoading: isLoadingStats } = useOrFetchMultipleDeploymentStats(deploymentIds);

  return (
    <div className="flex flex-col w-full h-screen overflow-auto">
      <div className="flex-1 mx-auto px-4 py-8 gap-6 bg-gray-50 w-full min-h-full">
        <HeaderSection
          title="Deployments"
          description="View and manage your AI agent deployments across different environments and configurations"
        />

        <div className="mt-6 flex-1 flex flex-col">
          <DeploymentsTable
            deployments={deployments}
            deploymentStats={allStats}
            total={total}
            currentPage={currentPage}
            pageSize={pageSize}
            isLoading={isLoading || isLoadingStats}
            error={error ?? undefined}
            onPageChange={setPage}
          />
        </div>
      </div>
    </div>
  );
}
