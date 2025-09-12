"use client";

import React from "react";
import { useToast } from "@/components/ToastProvider";

interface UpdateAgentTooltipProps {
  agentId: string;
  experimentId?: string;
}

export function UpdateAgentTooltip({ agentId, experimentId }: UpdateAgentTooltipProps) {
  const { showToast } = useToast();

  const promptText = experimentId
    ? `Adjust anotherai/agent/${agentId} based on the annotations that have been added in anotherai/experiment/${experimentId}.`
    : `Adjust anotherai/agent/${agentId} based on the annotations that have been added.`;

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(promptText);
      showToast("Prompt copied to clipboard");
    } catch (err) {
      console.error("Failed to copy prompt: ", err);
      showToast("Failed to copy prompt");
    }
  };

  return (
    <div className="max-w-xs min-w-xs py-1.5 px-1">
      <div className="text-xs font-medium text-white">
        <div>To update your agent:</div>
        <div className="ml-2 mt-1">
          <div className="flex">
            <span className="mr-1 flex-shrink-0">1.</span>
            <span className="flex-1 w-full whitespace-pre-wrap">
              Open your preferred MCP client (e.g., Cursor or Claude Code).
            </span>
          </div>
          <div className="flex mt-1">
            <span className="mr-1 flex-shrink-0">2.</span>
            <span className="flex-1 w-full whitespace-pre-wrap">{`Copy and paste the prompt below into the client's chat, and fill in the details you'd like to update:`}</span>
          </div>
        </div>
        <div className="mt-3 italic font-bold w-full whitespace-pre-wrap">{promptText}</div>
      </div>

      <div className="flex gap-2 mt-4 w-full items-center justify-end">
        <button
          onClick={handleCopyPrompt}
          className="flex items-center gap-1 bg-gray-700 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-800 transition-colors cursor-pointer"
        >
          Copy Prompt
        </button>
      </div>
    </div>
  );
}
