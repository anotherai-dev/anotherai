import { ActivityIndicator } from "@/components/ActivityIndicator";

interface AgentCellData {
  name: string;
  completionsLast3Days: number;
}

interface AgentsTableAgentCellProps {
  value: AgentCellData;
}

export function AgentsTableAgentCell({ value }: AgentsTableAgentCellProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-900 min-w-0 break-words font-semibold">
      <ActivityIndicator completionsLast3Days={value.completionsLast3Days} />
      <span>{value.name}</span>
    </div>
  );
}
