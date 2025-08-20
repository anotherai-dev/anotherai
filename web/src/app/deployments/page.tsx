"use client";

import { useMemo } from "react";
import { HeaderSection } from "@/components/HeaderSection";
import { useOrFetchMultipleAgentStats } from "@/store/agents_stats";
import { useOrFetchMockedDeployments } from "@/store/mocked_deployments";
import { DeploymentsTable } from "./sections/table/DeploymentsTable";

export default function DeploymentsPage() {
  const { deployments, isLoading, error } = useOrFetchMockedDeployments();

  // Get agent IDs from deployments for stats fetching
  const agentIds = useMemo(() => deployments.map((deployment) => deployment.agent_id), [deployments]);

  // Fetch stats for all agents used in deployments
  const { allStats, isLoading: isLoadingStats } = useOrFetchMultipleAgentStats(agentIds);

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 gap-6 bg-gray-50">
      <HeaderSection
        title="Deployments"
        description="View and manage your AI agent deployments across different environments and configurations"
      />

      <DeploymentsTable
        deployments={deployments}
        agentsStats={allStats}
        isLoading={isLoading || isLoadingStats}
        error={error ?? undefined}
      />
    </div>
  );
}
