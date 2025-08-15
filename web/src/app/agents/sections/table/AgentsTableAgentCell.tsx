import { AgentActivityIndicator } from "@/components/AgentActivityIndicator";

interface AgentCellData {
  name: string;
  active: boolean | null;
}

interface AgentsTableAgentCellProps {
  value: AgentCellData;
}

export function AgentsTableAgentCell({ value }: AgentsTableAgentCellProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-900 min-w-0 break-words font-semibold">
      {value.active !== null && <AgentActivityIndicator isActive={value.active} />}
      <span>{value.name}</span>
    </div>
  );
}
