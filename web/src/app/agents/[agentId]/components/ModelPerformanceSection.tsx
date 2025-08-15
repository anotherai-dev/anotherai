import { UniversalBarChart } from "@/components/universal-charts/UniversalBarChart";
import { SectionHeader } from "./SectionHeader";

interface DailyCost {
  date: string;
  total_cost: number;
  completion_count: number;
}

interface ModelPerformanceSectionProps {
  dailyCosts: DailyCost[];
}

export function ModelPerformanceSection({ dailyCosts }: ModelPerformanceSectionProps) {
  // Transform data for the universal chart - showing completions per day for last 30 days
  const chartData = dailyCosts.slice(-30).map((day) => ({
    x: new Date(day.date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    y: day.completion_count,
    date: day.date,
    total_cost: day.total_cost,
  }));

  return (
    <div className="bg-white border border-gray-200 rounded-[2px] flex flex-col">
      <div className="p-4">
        <SectionHeader
          title="Daily Completion Activity"
          description="Number of completions per day for the last 30 days"
        />
      </div>
      <UniversalBarChart
        data={chartData}
        yAxisFormatter={(value) => `${value}`}
        tooltipFormatter={(value) => `${value} completions`}
        barColor="#10b98180"
        emptyMessage="No completion data available"
        height="400px"
      />
    </div>
  );
}
