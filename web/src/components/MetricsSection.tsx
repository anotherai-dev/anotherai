import { ReactNode } from "react";

interface MetricsSectionProps {
  title: string;
  children: ReactNode;
}

export function MetricsSection({ title, children }: MetricsSectionProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-[4px] p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">{title}</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">{children}</div>
    </div>
  );
}
