import { ActivityIndicator } from "@/components/ActivityIndicator";
import { TextBreak } from "@/components/utils/TextBreak";

interface AgentCellData {
  name: string;
  completionsLast3Days: number;
}

interface AgentsTableAgentCellProps {
  value: AgentCellData;
}

export function AgentsTableAgentCell({ value }: AgentsTableAgentCellProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-900 min-w-0 font-semibold">
      <ActivityIndicator completionsLast3Days={value.completionsLast3Days} />
      <TextBreak>{value.name}</TextBreak>
    </div>
  );
}
