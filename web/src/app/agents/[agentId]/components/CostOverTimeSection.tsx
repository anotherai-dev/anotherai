import { UniversalBarChart } from "@/components/universal-charts/UniversalBarChart";
import { SectionHeader } from "./SectionHeader";

interface DailyCost {
  date: string;
  total_cost: number;
  completion_count: number;
}

interface CostOverTimeSectionProps {
  dailyCosts: DailyCost[];
}

export function CostOverTimeSection({ dailyCosts }: CostOverTimeSectionProps) {
  // Transform data for the universal chart
  const chartData = dailyCosts.slice(-30).map((day) => ({
    x: new Date(day.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    y: day.total_cost,
    completions: day.completion_count,
  }));

  return (
    <div className="bg-white border border-gray-200 rounded-[2px] flex flex-col">
      <div className="p-4">
        <SectionHeader title="Cost Over Time" description="Daily costs for the last 30 days" />
      </div>
      <UniversalBarChart
        data={chartData}
        yAxisFormatter={(value) => `$${value.toFixed(2)}`}
        tooltipFormatter={(value) => `$${value.toFixed(2)}`}
        barColor="#3b82f680"
        emptyMessage="No cost data available"
        height="400px"
      />
    </div>
  );
}
