"use client";

import React from "react";
import { useToast } from "@/components/ToastProvider";

interface ImproveAgentAnnotationsInstructionsContentProps {
  agentId: string;
  experimentId?: string;
}

export function ImproveAgentAnnotationsInstructionsContent({
  agentId,
  experimentId,
}: ImproveAgentAnnotationsInstructionsContentProps) {
  const { showToast } = useToast();

  const promptText = experimentId
    ? `Adjust anotherai/agent/${agentId} based on the annotations that have been added in anotherai/experiment/${experimentId}. `
    : `Adjust anotherai/agent/${agentId} based on the annotations that have been added. `;
  const copyButtonText = "Copy Annotation Prompt";
  const learnMoreUrl = "https://docs.anotherai.dev/use-cases/fundamentals/annotations";
  const learnMoreButtonText = "Learn More About Annotations";
  const copySuccessMessage = "Annotation prompt copied to clipboard";

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(promptText);
      showToast(copySuccessMessage);
    } catch (err) {
      console.error("Failed to copy prompt: ", err);
      showToast("Failed to copy prompt");
    }
  };

  const handleLearnMore = () => {
    window.open(learnMoreUrl, "_blank");
  };

  return (
    <div className="w-[365px] py-1.5 px-1">
      <div className="text-xs font-medium text-white">
        <div className="whitespace-pre-wrap break-words">
          Annotations allow you to add comments to your completions and experiments, that can then be used by your AI
          coding agent to improve the agent you&apos;re building.
        </div>

        <div className="mt-3">
          <div className="font-medium mb-1">How to use:</div>
          <div className="ml-2 space-y-1 text-xs font-normal">
            <div className="flex">
              <span className="mr-1 flex-shrink-0">1.</span>
              <span className="flex-1 w-full whitespace-pre-wrap break-words">
                Leave annotations on each completion about what&apos;s working and what isn&apos;t
              </span>
            </div>
            <div className="flex">
              <span className="mr-1 flex-shrink-0">2.</span>
              <span className="flex-1 w-full whitespace-pre-wrap break-words">
                Copy and paste the prompt below into the client&apos;s chat, and fill in the details you&apos;d like to
                update:
              </span>
            </div>
          </div>
        </div>

        <div className="mt-3 italic font-bold w-full whitespace-pre-wrap">
          Adjust anotherai/agent/{agentId} based on the annotations that have been added in anotherai/experiment/
          {experimentId}....[describe the specific improvements you want here]
        </div>
      </div>

      <div className="flex gap-2 mt-4 w-full items-center justify-end">
        <button
          onClick={handleLearnMore}
          className="flex items-center gap-1 bg-gray-700 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-800 transition-colors cursor-pointer"
        >
          {learnMoreButtonText}
        </button>
        <button
          onClick={handleCopyPrompt}
          className="flex items-center gap-1 bg-gray-700 text-white font-bold px-3 py-1.5 rounded-[2px] text-xs hover:bg-gray-800 transition-colors cursor-pointer"
        >
          {copyButtonText}
        </button>
      </div>
    </div>
  );
}
