"use client";

import { Plus } from "lucide-react";
import React from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { useToast } from "@/components/ToastProvider";

export function CreateViewInstructions() {
  const { showToast } = useToast();

  const promptText = `Can you add a view in AnotherAI that shows `;

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(promptText);
      showToast("Prompt copied to clipboard");
    } catch (err) {
      console.error("Failed to copy prompt: ", err);
      showToast("Failed to copy prompt");
    }
  };

  const instructionsContent = (
    <div className="w-[280px] py-1.5 px-1">
      <div className="text-xs font-medium text-white">
        <div>To add a new view:</div>
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
              Copy and paste the prompt below into the client&apos;s chat, and fill in the details you&apos;d like to
              update:
            </span>
          </div>
        </div>
        <div className="mt-3 italic font-bold w-full whitespace-pre-wrap">
          Can you add a view in AnotherAI that shows...[your changes here]
        </div>

        <div className="mt-3">
          <div className="font-medium mb-1">Examples of prompts:</div>
          <div className="ml-2 space-y-1 text-xs font-normal">
            <div className="whitespace-pre-wrap break-words">
              • Can you add a view in AnotherAI that lists all annotations on my agent, along with the input and output?
            </div>
            <div className="whitespace-pre-wrap break-words">
              • Can you add a view in AnotherAI that shows how much each of my agents cost every day for the last two
              weeks?
            </div>
          </div>
        </div>
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

  return (
    <HoverPopover
      content={instructionsContent}
      position="bottom"
      popoverClassName="bg-gray-900 text-white rounded-[4px]"
    >
      <button
        onClick={() => {}}
        className="p-1 rounded hover:bg-gray-200 hover:text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer flex items-center gap-0.5"
      >
        <Plus className="w-3 h-3" />
        View
      </button>
    </HoverPopover>
  );
}
