"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageError } from "@/components/PageError";
import { SimpleTableComponent } from "@/components/SimpleTableComponent";
import { formatRelativeDate, formatTotalCost } from "@/components/utils/utils";
import AgentsBaseCell from "./AgentsBaseCell";
import { AgentsTableAgentCell } from "./AgentsTableAgentCell";

// Column key constants
export const AGENTS_COLUMNS = {
  AI_AGENT: "AI Agent",
  COMPLETIONS_LAST_7_DAYS: "Total Completions",
  TOTAL_COST: "Total Cost",
  CREATED_AT: "Created at",
} as const;

interface Agent {
  id: string;
  name: string;
  created_at: string;
}

interface AgentStats {
  total_completions: number;
  completions_last_3_days: number;
  total_cost: number;
  active: boolean;
  last_completion_date: string | null;
}

interface AgentsTableProps {
  agents: Agent[];
  agentsStats?: Map<string, AgentStats>;
  isLoading: boolean;
  error?: Error;
}

export function AgentsTable(props: AgentsTableProps) {
  const { agents, agentsStats, isLoading, error } = props;
  const router = useRouter();

  // Define display columns
  const columnHeaders = useMemo(() => {
    return [
      AGENTS_COLUMNS.AI_AGENT,
      AGENTS_COLUMNS.COMPLETIONS_LAST_7_DAYS,
      AGENTS_COLUMNS.TOTAL_COST,
      AGENTS_COLUMNS.CREATED_AT,
    ];
  }, []);

  // Transform agent data for display
  const displayData = useMemo(() => {
    const agentDisplayData = agents.map((agent) => {
      const stats = agentsStats?.get(agent.id);
      return {
        [AGENTS_COLUMNS.AI_AGENT]: {
          name: agent.name && agent.name.trim() ? agent.name : agent.id,
          completionsLast3Days: stats?.completions_last_3_days ?? 0,
        },
        [AGENTS_COLUMNS.COMPLETIONS_LAST_7_DAYS]: stats?.total_completions ?? null,
        [AGENTS_COLUMNS.TOTAL_COST]: stats?.total_cost ?? null,
        [AGENTS_COLUMNS.CREATED_AT]: agent.created_at,
        _originalAgent: agent,
        _lastCompletionDate: stats?.last_completion_date,
      };
    });

    // Sort by last completion date (most recent first), then by agent name
    return agentDisplayData.sort((a, b) => {
      // First sort by last completion date (most recent first)
      const dateA = a._lastCompletionDate ? new Date(a._lastCompletionDate).getTime() : 0;
      const dateB = b._lastCompletionDate ? new Date(b._lastCompletionDate).getTime() : 0;

      if (dateA !== dateB) {
        return dateB - dateA; // Most recent first
      }

      // If dates are equal (or both null), sort by agent name
      const nameA = (a[AGENTS_COLUMNS.AI_AGENT] as { name: string }).name;
      const nameB = (b[AGENTS_COLUMNS.AI_AGENT] as { name: string }).name;
      return String(nameA).localeCompare(String(nameB));
    });
  }, [agents, agentsStats]);

  const handleRowClick = (rowIndex: number) => {
    const displayRow = displayData[rowIndex];
    const agent = displayRow._originalAgent;
    const agentId = agent.id;

    if (!agentId) {
      return;
    }

    router.push(`/agents/${encodeURIComponent(agentId)}`, { scroll: false });
  };

  if (error) {
    return <PageError error={error} />;
  }

  if (isLoading) {
    return <LoadingState />;
  }

  if (!isLoading && displayData.length === 0) {
    return (
      <EmptyState
        title="No agents found."
        subtitle="Create your first agent to get started"
        documentationUrl="https://docs.anotherai.dev/use-cases/fundamentals/building"
      />
    );
  }

  if (displayData.length === 0) {
    return null;
  }

  return (
    <SimpleTableComponent
      columnHeaders={columnHeaders}
      data={displayData.map((row) =>
        columnHeaders.map((header) => {
          const value = row[header as keyof typeof row];

          switch (header) {
            case AGENTS_COLUMNS.AI_AGENT:
              return (
                <AgentsTableAgentCell key={header} value={value as { name: string; completionsLast3Days: number }} />
              );

            case AGENTS_COLUMNS.COMPLETIONS_LAST_7_DAYS:
              return <AgentsBaseCell key={header} value={value} />;

            case AGENTS_COLUMNS.TOTAL_COST:
              return <AgentsBaseCell key={header} value={value} formatter={formatTotalCost} />;

            case AGENTS_COLUMNS.CREATED_AT:
              return <AgentsBaseCell key={header} value={value} formatter={formatRelativeDate} />;

            default:
              return <AgentsBaseCell key={header} value={value} />;
          }
        })
      )}
      minCellWidth={120}
      onRowClick={handleRowClick}
      cellVerticalAlign="middle"
      columnWidths={["auto", "150px", "120px", "160px"]}
    />
  );
}
