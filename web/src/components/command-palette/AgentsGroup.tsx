import { Command } from "cmdk";
import { AgentWithCompletionCount } from "@/types/models";
import { CommandPaletteItem } from "./CommandPaletteItem";

interface AgentsGroupProps {
  agents: AgentWithCompletionCount[];
  onSelect: (value: string) => void;
}

export function AgentsGroup({ agents, onSelect }: AgentsGroupProps) {
  if (agents.length === 0) return null;

  return (
    <Command.Group heading="Agents">
      {agents.map((agent) => (
        <CommandPaletteItem
          key={agent.agent_id}
          value={`agent:${agent.agent_id} ${agent.agent_id} agent completions executions`}
          onSelect={() => onSelect(`agent:${agent.agent_id}`)}
          icon={
            <svg
              className="w-4 h-4 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
          }
          title={agent.agent_id}
          subtitle={`${agent.completion_count} completions`}
        />
      ))}
    </Command.Group>
  );
}
