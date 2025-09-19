"use client";

import { Info } from "lucide-react";
import React from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { useToast } from "@/components/ToastProvider";

export function MetricsCustomViewsInstructions() {
  const { showToast } = useToast();

  const promptText = `Create a view that...`;

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(promptText);
      showToast("Prompt copied to clipboard");
    } catch (err) {
      console.error("Failed to copy prompt: ", err);
      showToast("Failed to copy prompt");
    }
  };

  const handleLearnMore = () => {
    window.open("https://docs.anotherai.dev/use-cases/fundamentals/metrics", "_blank");
  };

  const instructionsContent = (
    <div className="w-xs py-1.5 px-1">
      <div className="text-xs font-medium text-white">
        <div>Want to filter your completions?</div>
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
              filtered:
            </span>
          </div>
        </div>
        <div className="mt-3 italic font-bold w-full whitespace-pre-wrap">
          Create a view that...[describe the data you want to see represented]
        </div>
      </div>

      <div className="flex gap-2 mt-4 w-full items-center justify-between">
        <button
          onClick={handleLearnMore}
          className="flex items-center gap-1 bg-gray-600 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-700 transition-colors cursor-pointer"
        >
          Learn More About Custom Views
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
        className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-3 py-2 rounded-[2px] flex items-center justify-center shadow-sm shadow-black/5"
        title="Make your own custom views"
      >
        <div className="flex items-center gap-2">
          <Info size={14} />
          <span className="text-[13px] font-medium">Make your own custom views</span>
        </div>
      </button>
    </HoverPopover>
  );
}
