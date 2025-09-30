"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
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

type SortDirection = "asc" | "desc";
type SortableColumn = keyof typeof AGENTS_COLUMNS;

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

  // Sorting state
  const [sortColumn, setSortColumn] = useState<SortableColumn>("CREATED_AT");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

  // Sorting handler
  const handleSort = useCallback(
    (column: SortableColumn) => {
      if (sortColumn === column) {
        setSortDirection(sortDirection === "asc" ? "desc" : "asc");
      } else {
        setSortColumn(column);
        setSortDirection("asc");
      }
    },
    [sortColumn, sortDirection]
  );

  // Define display columns with sortable headers
  const columnHeaders = useMemo(() => {
    // Create sortable header component
    const SortableHeader = ({ column, children }: { column: SortableColumn; children: React.ReactNode }) => (
      <button
        onClick={() => handleSort(column)}
        className="flex items-center gap-1 text-left w-full hover:text-gray-700 transition-colors cursor-pointer"
      >
        <span>{children}</span>
        <div className="flex flex-col ml-1">
          <ChevronUp
            size={12}
            className={`${
              sortColumn === column && sortDirection === "asc" ? "text-gray-900" : "text-gray-400"
            } transition-colors`}
          />
          <ChevronDown
            size={12}
            className={`${
              sortColumn === column && sortDirection === "desc" ? "text-gray-900" : "text-gray-400"
            } transition-colors -mt-1`}
          />
        </div>
      </button>
    );

    return [
      <SortableHeader key="AI_AGENT" column="AI_AGENT">
        {AGENTS_COLUMNS.AI_AGENT}
      </SortableHeader>,
      <SortableHeader key="COMPLETIONS_LAST_7_DAYS" column="COMPLETIONS_LAST_7_DAYS">
        {AGENTS_COLUMNS.COMPLETIONS_LAST_7_DAYS}
      </SortableHeader>,
      <SortableHeader key="TOTAL_COST" column="TOTAL_COST">
        {AGENTS_COLUMNS.TOTAL_COST}
      </SortableHeader>,
      <SortableHeader key="CREATED_AT" column="CREATED_AT">
        {AGENTS_COLUMNS.CREATED_AT}
      </SortableHeader>,
    ];
  }, [sortColumn, sortDirection, handleSort]);

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

    // Apply sorting based on current sort column and direction
    const sortedData = agentDisplayData.sort((a, b) => {
      let valueA: string | number;
      let valueB: string | number;

      switch (sortColumn) {
        case "AI_AGENT":
          valueA = (a[AGENTS_COLUMNS.AI_AGENT] as { name: string }).name.toLowerCase();
          valueB = (b[AGENTS_COLUMNS.AI_AGENT] as { name: string }).name.toLowerCase();
          break;
        case "COMPLETIONS_LAST_7_DAYS":
          valueA = a[AGENTS_COLUMNS.COMPLETIONS_LAST_7_DAYS] ?? 0;
          valueB = b[AGENTS_COLUMNS.COMPLETIONS_LAST_7_DAYS] ?? 0;
          break;
        case "TOTAL_COST":
          valueA = a[AGENTS_COLUMNS.TOTAL_COST] ?? 0;
          valueB = b[AGENTS_COLUMNS.TOTAL_COST] ?? 0;
          break;
        case "CREATED_AT":
          valueA = new Date(a[AGENTS_COLUMNS.CREATED_AT]).getTime();
          valueB = new Date(b[AGENTS_COLUMNS.CREATED_AT]).getTime();
          break;
        default:
          return 0;
      }

      // Handle string comparison
      if (typeof valueA === "string" && typeof valueB === "string") {
        const comparison = valueA.localeCompare(valueB);
        return sortDirection === "asc" ? comparison : -comparison;
      }

      // Handle numeric comparison
      if (typeof valueA === "number" && typeof valueB === "number") {
        const comparison = valueA - valueB;
        return sortDirection === "asc" ? comparison : -comparison;
      }

      // Fallback
      return 0;
    });

    return sortedData;
  }, [agents, agentsStats, sortColumn, sortDirection]);

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
        Object.keys(AGENTS_COLUMNS).map((columnKeyName) => {
          const columnKey = AGENTS_COLUMNS[columnKeyName as keyof typeof AGENTS_COLUMNS];
          const value = row[columnKey as keyof typeof row];

          switch (columnKey) {
            case AGENTS_COLUMNS.AI_AGENT:
              return (
                <AgentsTableAgentCell key={columnKey} value={value as { name: string; completionsLast3Days: number }} />
              );

            case AGENTS_COLUMNS.COMPLETIONS_LAST_7_DAYS:
              return <AgentsBaseCell key={columnKey} value={value} />;

            case AGENTS_COLUMNS.TOTAL_COST:
              return <AgentsBaseCell key={columnKey} value={value} formatter={formatTotalCost} />;

            case AGENTS_COLUMNS.CREATED_AT:
              return <AgentsBaseCell key={columnKey} value={value} formatter={formatRelativeDate} />;

            default:
              return <AgentsBaseCell key={columnKey} value={value} />;
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
