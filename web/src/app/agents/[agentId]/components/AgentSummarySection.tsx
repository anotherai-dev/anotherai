import { AgentSummary } from "@/store/agent_stats";

interface AgentSummarySectionProps {
  summary: AgentSummary;
}

export function AgentSummarySection({ summary }: AgentSummarySectionProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-[2px] p-2">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-0">
        <div className="text-center py-3 px-4 border-r border-gray-200 last:border-r-0 lg:border-r">
          <p className="text-xl font-semibold text-gray-900">
            {summary.total_runs.toLocaleString()}
          </p>
          <p className="text-xs text-gray-600">Total Completions</p>
        </div>
        <div className="text-center py-3 px-4 border-r border-gray-200 last:border-r-0 lg:border-r">
          <p className="text-xl font-semibold text-gray-900">
            ${Math.max(summary.total_cost, 0.01).toFixed(2)}
          </p>
          <p className="text-xs text-gray-600">Total Cost</p>
        </div>
        <div className="text-center py-3 px-4 border-r border-gray-200 last:border-r-0 lg:border-r">
          <p className="text-xl font-semibold text-gray-900">
            ${summary.avg_cost_per_run.toFixed(4)}
          </p>
          <p className="text-xs text-gray-600">Average Cost per Completion</p>
        </div>
        <div className="text-center py-3 px-4 border-r border-gray-200 last:border-r-0">
          <p className="text-xl font-semibold text-gray-900">
            {summary.avg_duration.toFixed(1)}s
          </p>
          <p className="text-xs text-gray-600">Average Duration</p>
        </div>
      </div>
    </div>
  );
}
