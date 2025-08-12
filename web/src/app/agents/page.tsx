"use client";

import { useMemo } from "react";
import { HeaderSection } from "@/components/HeaderSection";
import { useOrFetchAgents } from "@/store/agents";
import { useOrFetchMultipleAgentStats } from "@/store/agents_stats";
import { AgentsTable } from "./sections/table/AgentsTable";

export default function AgentsPage() {
  const { agents, isLoading, error } = useOrFetchAgents();

  // Get agent IDs for stats fetching
  const agentIds = useMemo(() => agents.map((agent) => agent.id), [agents]);

  // Fetch stats for all agents
  const { allStats, isLoading: isLoadingStats } =
    useOrFetchMultipleAgentStats(agentIds);

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 gap-6 bg-gray-50">
      <HeaderSection
        title="Agents"
        description="View and manage your AI agents, monitor their performance, and analyze their completion statistics"
      />

      <AgentsTable
        agents={agents}
        agentsStats={allStats}
        isLoading={isLoading || isLoadingStats}
        error={error}
      />
    </div>
  );
}
