"use client";

import { Info } from "lucide-react";
import React from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { useToast } from "@/components/ToastProvider";

interface DeploymentInfoTooltipProps {
  deploymentId: string;
  agentId: string;
}

export function DeploymentInfoTooltip({ deploymentId, agentId }: DeploymentInfoTooltipProps) {
  const { showToast } = useToast();

  const debugPromptText = `Debug what's going on with my deployed version of anotherai/agents/${agentId}/versions/${deploymentId}. Once you've figured out the problem, create an improved version and a new experiment comparing the current deployed version with the improved version. The problem I'm seeing is: `;

  const newModelPromptText = `Retry the last 10 completions of anotherai/agents/${agentId}/versions/${deploymentId} and compare the outputs with `;

  const handleCopyDebugPrompt = async () => {
    try {
      await navigator.clipboard.writeText(debugPromptText);
      showToast("Debug prompt copied to clipboard");
    } catch (err) {
      console.error("Failed to copy debug prompt: ", err);
      showToast("Failed to copy debug prompt");
    }
  };

  const handleCopyNewModelPrompt = async () => {
    try {
      await navigator.clipboard.writeText(newModelPromptText);
      showToast("New model prompt copied to clipboard");
    } catch (err) {
      console.error("Failed to copy new model prompt: ", err);
      showToast("Failed to copy new model prompt");
    }
  };

  const instructionsContent = (
    <div className="w-xs py-1.5 px-1">
      {/* First Section: Debug Prompt */}
      <div className="mb-6">
        <div className="text-xs font-medium text-white">
          <div>Something&apos;s not right with your deployed version?</div>
          <div className="ml-2 mt-1">
            <div className="flex">
              <span className="mr-1 flex-shrink-0">1.</span>
              <span className="flex-1 w-full whitespace-pre-wrap">
                Open your preferred MCP client (e.g., Cursor or Claude Code).
              </span>
            </div>
            <div className="flex mt-1">
              <span className="mr-1 flex-shrink-0">2.</span>
              <span className="flex-1 w-full whitespace-pre-wrap">
                Copy and paste the prompt below into the client&apos;s chat, and fill in the details you&apos;d like
                debugged and fixed.
              </span>
            </div>
          </div>
          <div className="mt-3 italic font-bold w-full whitespace-pre-wrap break-words">
            Debug what&apos;s going on with my deployed version of anotherai/agents/{agentId}/versions/{deploymentId}
            ...[describe the problem you&apos;re seeing here]
          </div>
        </div>

        <div className="flex gap-2 mt-4 w-full items-center justify-end">
          <button
            onClick={handleCopyDebugPrompt}
            className="flex items-center gap-1 bg-gray-700 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-800 transition-colors cursor-pointer"
          >
            Copy Debug Prompt
          </button>
        </div>
      </div>

      {/* Second Section: New Model Prompt */}
      <div>
        <div className="text-xs font-medium text-white">
          <div>Want to test your agent with a newly released model?</div>
          <div className="ml-2 mt-1">
            <div className="flex">
              <span className="mr-1 flex-shrink-0">1.</span>
              <span className="flex-1 w-full whitespace-pre-wrap">
                Open your preferred MCP client (e.g., Cursor or Claude Code).
              </span>
            </div>
            <div className="flex mt-1">
              <span className="mr-1 flex-shrink-0">2.</span>
              <span className="flex-1 w-full whitespace-pre-wrap">
                Copy and paste the prompt below into the client&apos;s chat, and fill in the name of the model
                you&apos;d like to test (and optionally edit the number of completions you&apos;d like to test with).
              </span>
            </div>
          </div>
          <div className="mt-3 italic font-bold w-full whitespace-pre-wrap break-words">
            Retry the last 10 completions of anotherai/agents/{agentId}/versions/{deploymentId} and compare the outputs
            with [add the model you&apos;d like to try].
          </div>
        </div>

        <div className="flex gap-2 mt-4 w-full items-center justify-end">
          <button
            onClick={handleCopyNewModelPrompt}
            className="flex items-center gap-1 bg-gray-700 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-800 transition-colors cursor-pointer"
          >
            Copy New Model Prompt
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <HoverPopover
      content={instructionsContent}
      position="bottom"
      popoverClassName="bg-gray-900 text-white rounded-[4px]"
    >
      <button
        onClick={() => {}}
        className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] h-8 flex items-center justify-center shadow-sm shadow-black/5"
        title={`Update ${agentId}'s deployment`}
      >
        <div className="flex items-center gap-2 px-0.5">
          <Info size={12} />
          <span className="text-xs font-medium">Update {agentId}&apos;s deployment</span>
        </div>
      </button>
    </HoverPopover>
  );
}
