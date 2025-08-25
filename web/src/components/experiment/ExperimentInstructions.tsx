"use client";

import { Info } from "lucide-react";
import React from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { useToast } from "@/components/ToastProvider";

interface ExperimentInstructionsProps {
  agentName: string;
}

export function ExperimentInstructions({ agentName }: ExperimentInstructionsProps) {
  const { showToast } = useToast();

  const promptText = `Create an experiment with anotherai/agent/${agentName} in AnotherAI that tests `;

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(promptText);
      showToast("Experiment prompt copied to clipboard");
    } catch (err) {
      console.error("Failed to copy prompt: ", err);
      showToast("Failed to copy prompt");
    }
  };

  const handleLearnMore = () => {
    window.open("https://docs.anotherai.dev/experiments", "_blank");
  };

  const instructionsContent = (
    <div className="w-[300px] py-1.5 px-1">
      <div className="text-xs font-medium text-white">
        <div className="whitespace-pre-wrap break-words">Want to test changes to your agent?</div>

        <div className="ml-2 mt-1">
          <div className="flex">
            <span className="mr-1 flex-shrink-0">1.</span>
            <span className="flex-1 w-full whitespace-pre-wrap break-words">
              Open your preferred MCP client (e.g., Cursor or Claude Code).
            </span>
          </div>
          <div className="flex mt-1">
            <span className="mr-1 flex-shrink-0">2.</span>
            <span className="flex-1 w-full whitespace-pre-wrap break-words">
              Copy and paste the prompt below into the client&apos;s chat, and describe the updates you&apos;d like to
              test
            </span>
          </div>
        </div>

        <div className="mt-3 italic font-bold w-full whitespace-pre-wrap">
          Create an experiment with anotherai/agent/{agentName} in AnotherAI that tests...[describe what you&apos;d like
          to experiment with]
        </div>
      </div>

      <div className="flex gap-2 mt-4 w-full items-center justify-end">
        <button
          onClick={handleLearnMore}
          className="flex items-center gap-1 bg-gray-700 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-800 transition-colors cursor-pointer"
        >
          Learn More About Experiments
        </button>
        <button
          onClick={handleCopyPrompt}
          className="flex items-center gap-1 bg-gray-700 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-800 transition-colors cursor-pointer"
        >
          Copy Prompt
        </button>
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
        title="Want to change something?"
      >
        <div className="flex items-center gap-2 px-0.5">
          <Info size={12} />
          <span className="text-xs font-medium">Want to change something?</span>
        </div>
      </button>
    </HoverPopover>
  );
}
