"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { PageError } from "@/components/PageError";
import { PageHeader } from "@/components/PageHeader";
import { useOrFetchAgentDetails } from "@/store/agent_stats";
import { buildQuery } from "@/utils/queries";
import { CompletionsTable } from "../../completions/sections/table/CompletionsTable";
import { AgentSummarySection } from "./components/AgentSummarySection";
import { CostOverTimeSection } from "./components/CostOverTimeSection";
import { ModelPerformanceSection } from "./components/ModelPerformanceSection";
import { SectionHeader } from "./components/SectionHeader";

export default function AgentDetailPage() {
  const params = useParams();
  const agentId = params.agentId as string;

  // Use the same default query as completions page with agent_id filter
  const defaultQueryWithAgentFilter = buildQuery(`agent_id = '${agentId}'`);

  const { details, isLoading, error } = useOrFetchAgentDetails(agentId);

  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 bg-gray-50 overflow-y-auto">
      <PageHeader
        breadcrumbs={[{ label: "Agents", href: "/agents" }, { label: agentId }]}
        title="Agent Details"
        description="View agent performance metrics and completions"
        copyablePrefixAndId={`anotherai/agent/${agentId}`}
      />

      {error && <PageError error={error.message} />}

      {isLoading && (
        <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
          <LoadingIndicator />
        </div>
      )}

      {details && !isLoading && (
        <div className="flex flex-col gap-8">
          <AgentSummarySection summary={details.summary} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CostOverTimeSection dailyCosts={details.daily_costs} />
            <ModelPerformanceSection dailyCosts={details.daily_costs} />
          </div>

          <div>
            <SectionHeader
              title="Recent Completions"
              description={`Last ${details.last_completions.length} completions for this agent`}
            />
            <CompletionsTable
              data={details.last_completions}
              isLoading={isLoading}
              error={error}
              maxHeight="800px"
            />
            <div className="mt-4 text-left">
              <Link
                href={`/completions?query=${encodeURIComponent(defaultQueryWithAgentFilter)}`}
                className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-3 py-2 rounded-[2px] text-sm shadow-sm shadow-black/5"
              >
                View all completions
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
