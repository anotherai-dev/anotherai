"use client";

import { useMemo } from "react";
import { useCompletionsQuery } from "@/store/completions";

export function MetricsSummary() {
  // Original metrics
  const { data: totalCostData, isLoading: isLoadingTotalCost } = useCompletionsQuery(
    "SELECT COALESCE(SUM(cost_usd), 0) AS total_cost FROM completions"
  );
  const { data: totalCompletionsData, isLoading: isLoadingTotalCompletions } = useCompletionsQuery(
    "SELECT COUNT(*) AS total_completions FROM completions"
  );
  const { data: avgCostData, isLoading: isLoadingAvgCost } = useCompletionsQuery(
    "SELECT COALESCE(AVG(cost_usd), 0) AS avg_cost FROM completions WHERE cost_usd > 0"
  );
  const { data: avgDurationData, isLoading: isLoadingAvgDuration } = useCompletionsQuery(
    "SELECT COALESCE(AVG(duration_seconds), 0) AS avg_duration FROM completions WHERE duration_seconds > 0"
  );
  const { data: successRateData, isLoading: isLoadingSuccessRate } = useCompletionsQuery(
    "SELECT COALESCE((COUNTIf(output_error = '') * 100.0 / COUNT(*)), 0) AS success_rate FROM completions"
  );
  const { data: activeAgentsData, isLoading: isLoadingActiveAgents } = useCompletionsQuery(
    "SELECT COUNT(DISTINCT agent_id) AS active_agents FROM completions"
  );

  // Additional metrics
  const { data: mostUsedModelData, isLoading: isLoadingMostUsedModel } = useCompletionsQuery(
    "SELECT version_model AS model, COUNT(*) AS count FROM completions GROUP BY version_model ORDER BY count DESC LIMIT 1"
  );
  const { data: totalFailedData, isLoading: isLoadingTotalFailed } = useCompletionsQuery(
    "SELECT COUNT(*) AS total_failed FROM completions WHERE output_error != ''"
  );
  const { data: mostActiveAgentData, isLoading: isLoadingMostActiveAgent } = useCompletionsQuery(
    "SELECT agent_id, COUNT(*) AS count FROM completions GROUP BY agent_id ORDER BY count DESC LIMIT 1"
  );
  const { data: avgDailyCompletionsData, isLoading: isLoadingAvgDaily } = useCompletionsQuery(
    "SELECT AVG(daily_count) AS avg_daily FROM (SELECT toDate(created_at) AS date, COUNT(*) AS daily_count FROM completions GROUP BY date)"
  );
  const { data: monthlySpendingData, isLoading: isLoadingMonthlySpending } = useCompletionsQuery(
    "SELECT COALESCE(SUM(cost_usd), 0) AS monthly_cost FROM completions WHERE toYYYYMM(created_at) = toYYYYMM(now())"
  );
  const { data: responseTimeRangeData, isLoading: isLoadingResponseTimeRange } = useCompletionsQuery(
    "SELECT MIN(duration_seconds) AS min_time, MAX(duration_seconds) AS max_time FROM completions WHERE duration_seconds > 0"
  );

  // Check if any queries are still loading
  const isLoading =
    isLoadingTotalCost ||
    isLoadingTotalCompletions ||
    isLoadingAvgCost ||
    isLoadingAvgDuration ||
    isLoadingSuccessRate ||
    isLoadingActiveAgents ||
    isLoadingMostUsedModel ||
    isLoadingTotalFailed ||
    isLoadingMostActiveAgent ||
    isLoadingAvgDaily ||
    isLoadingMonthlySpending ||
    isLoadingResponseTimeRange;

  // Extract values with proper type casting
  const totalCost = Number(totalCostData?.[0]?.total_cost || 0);
  const totalCompletions = Number(totalCompletionsData?.[0]?.total_completions || 0);
  const avgCost = Number(avgCostData?.[0]?.avg_cost || 0);
  const avgDuration = Number(avgDurationData?.[0]?.avg_duration || 0);
  const successRate = Number(successRateData?.[0]?.success_rate || 0);
  const activeAgents = Number(activeAgentsData?.[0]?.active_agents || 0);
  const mostUsedModel = String(mostUsedModelData?.[0]?.model || "N/A");
  const totalFailed = Number(totalFailedData?.[0]?.total_failed || 0);
  const mostActiveAgent = String(mostActiveAgentData?.[0]?.agent_id || "N/A");
  const avgDailyCompletions = Number(avgDailyCompletionsData?.[0]?.avg_daily || 0);
  const monthlySpending = Number(monthlySpendingData?.[0]?.monthly_cost || 0);
  const fastestResponse = Number(responseTimeRangeData?.[0]?.min_time || 0);
  const slowestResponse = Number(responseTimeRangeData?.[0]?.max_time || 0);

  const metrics = useMemo(
    () => [
      // Completion Overview
      { key: "Total Completions", value: totalCompletions.toLocaleString() },
      { key: "Avg Success Rate", value: `${successRate.toFixed(1)}%` },
      { key: "Total Failed", value: totalFailed.toLocaleString(), color: "text-red-600" },

      // Response Time Metrics
      { key: "Avg Response Time", value: `${avgDuration.toFixed(1)}s` },
      { key: "Fastest Response", value: `${fastestResponse.toFixed(1)}s`, color: "text-green-600" },
      { key: "Slowest Response", value: `${slowestResponse.toFixed(1)}s`, color: "text-red-600" },

      // Cost Metrics
      { key: "Total Cost", value: `$${totalCost.toFixed(2)}` },
      { key: "This Month's Cost", value: `$${monthlySpending.toFixed(2)}`, color: "text-blue-600" },
      { key: "Avg Cost per Completion", value: `$${avgCost.toFixed(4)}` },

      // Usage Analytics
      { key: "Avg Daily Completions", value: Math.round(avgDailyCompletions).toLocaleString() },
      { key: "Active Agents", value: activeAgents.toString() },
      { key: "Most Active Agent", value: mostActiveAgent },

      // Model Analytics
      { key: "Most Used Model", value: mostUsedModel },
    ],
    [
      totalCost,
      totalCompletions,
      successRate,
      avgDuration,
      mostUsedModel,
      totalFailed,
      mostActiveAgent,
      avgDailyCompletions,
      monthlySpending,
      activeAgents,
      avgCost,
      fastestResponse,
      slowestResponse,
    ]
  );

  // Loading skeleton component
  const LoadingSkeleton = () => <div className="animate-pulse bg-gray-200 h-4 rounded w-16"></div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-2">
      {metrics.map((metric) => (
        <div
          key={metric.key}
          className="flex justify-between items-center py-2 border-b border-gray-100 last:border-b-0"
        >
          <span className="text-[13px] text-gray-600 font-medium">{metric.key}:</span>
          {isLoading ? (
            <LoadingSkeleton />
          ) : (
            <span className={`text-[13px] font-semibold ${metric.color || "text-gray-900"}`}>{metric.value}</span>
          )}
        </div>
      ))}
    </div>
  );
}
