"use client";

import { MetricsCustomViewsInstructions } from "@/components/MetricsCustomViewsInstructions";
import { PageHeader } from "@/components/PageHeader";
import { QueryGraphCard } from "@/components/QueryGraphCard";
import { MetricsSection } from "./components/MetricsSection";
import { MetricsSummary } from "./components/MetricsSummary";

export default function MetricsPage() {
  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 pt-4 pb-8 gap-4 bg-gray-50 overflow-y-auto">
      <PageHeader
        breadcrumbs={[]}
        title="Metrics"
        description="Monitor and analyze performance metrics across your AI agents and completions"
        descriptionRightContent={<MetricsCustomViewsInstructions />}
        className="pb-2"
      />

      <MetricsSection title="Summary">
        <div className="lg:col-span-2">
          <MetricsSummary />
        </div>
      </MetricsSection>

      <MetricsSection title="Cost Analytics">
        <QueryGraphCard
          title="Daily Cost Trend"
          subtitle="Daily cost trend across all time periods (USD)"
          graphType="line"
          query="SELECT toDate(created_at) AS date, SUM(cost_usd) AS total_cost FROM completions GROUP BY date ORDER BY date ASC"
          customGraph={{
            type: "line",
            x: { field: "date", label: "Date" },
            y: [{ field: "total_cost", label: "Total Cost", unit: "$" }],
          }}
        />

        <QueryGraphCard
          title="Cost by Model"
          subtitle="Cost distribution across different AI models"
          graphType="pie"
          query="SELECT version_model AS model, SUM(cost_usd) AS total_cost FROM completions WHERE cost_usd > 0 GROUP BY model ORDER BY total_cost DESC LIMIT 10"
          customGraph={{
            type: "pie",
            x: { field: "model", label: "Model" },
            y: [{ field: "total_cost", label: "Total Cost", unit: "$" }],
          }}
        />

        <QueryGraphCard
          title="Cost by Agent"
          subtitle="Cost breakdown by agent/deployment"
          graphType="bar"
          query="SELECT agent_id, SUM(cost_usd) AS total_cost FROM completions GROUP BY agent_id ORDER BY total_cost DESC"
          customGraph={{
            type: "bar",
            x: { field: "agent_id", label: "Agent" },
            y: [{ field: "total_cost", label: "Total Cost", unit: "$" }],
            stacked: true,
          }}
        />
      </MetricsSection>

      <MetricsSection title="Usage Metrics">
        <QueryGraphCard
          title="Daily Completions"
          subtitle="Number of completions per day over all time"
          graphType="line"
          query="SELECT toDate(created_at) AS date, COUNT(*) AS completions FROM completions GROUP BY date ORDER BY date ASC"
          customGraph={{
            type: "line",
            x: { field: "date", label: "Date" },
            y: [{ field: "completions", label: "Completions" }],
          }}
        />

        <QueryGraphCard
          title="Completions by Model"
          subtitle="Completion counts per AI model"
          graphType="bar"
          query="SELECT version_model AS model, COUNT(*) AS completions FROM completions GROUP BY model ORDER BY completions DESC"
          customGraph={{
            type: "bar",
            x: { field: "model", label: "Model" },
            y: [{ field: "completions", label: "Completions" }],
          }}
        />

        <QueryGraphCard
          title="Completions by Agent"
          subtitle="Completion trends per agent over time"
          graphType="bar"
          query="SELECT toDate(created_at) AS date, agent_id, COUNT(*) AS completions FROM completions GROUP BY date, agent_id ORDER BY date ASC"
          customGraph={{
            type: "bar",
            x: { field: "date", label: "Date" },
            y: [{ field: "completions", label: "Completions" }],
            stacked: true,
          }}
        />
      </MetricsSection>

      <MetricsSection title="Performance Metrics">
        <QueryGraphCard
          title="Average Response Time"
          subtitle="Average response time by date (seconds)"
          graphType="line"
          query="SELECT toDate(created_at) AS date, AVG(duration_seconds) AS avg_response_time FROM completions GROUP BY date ORDER BY date ASC"
          customGraph={{
            type: "line",
            x: { field: "date", label: "Date" },
            y: [{ field: "avg_response_time", label: "Avg Response Time", unit: "s" }],
          }}
        />

        <QueryGraphCard
          title="Success Rate"
          subtitle="Successful vs failed completions over time"
          graphType="line"
          query="SELECT toDate(created_at) AS date, COUNTIf(output_error = '') AS success, COUNTIf(output_error != '') AS failed, COUNT(*) AS total, (COUNTIf(output_error = '') / COUNT(*)) AS success_rate FROM completions GROUP BY date ORDER BY date ASC"
          customGraph={{
            type: "line",
            x: { field: "date", label: "Date" },
            y: [
              { field: "success", label: "Successful Completions", color_hex: "#10B981" },
              { field: "failed", label: "Failed Completions", color_hex: "#EF4444" },
            ],
          }}
        />
      </MetricsSection>
    </div>
  );
}
