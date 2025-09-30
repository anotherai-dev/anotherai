"use client";

import { Info } from "lucide-react";
import React from "react";
import { HoverPopover } from "@/components/HoverPopover";
import { ImproveAgentAnnotationsInstructionsContent } from "./ImproveAgentAnnotationsInstructionsContent";

interface ImproveAgentAnnotationsInstructionsProps {
  agentId: string;
  experimentId: string;
}

export function ImproveAgentAnnotationsInstructions({
  agentId,
  experimentId,
}: ImproveAgentAnnotationsInstructionsProps) {
  return (
    <HoverPopover
      content={<ImproveAgentAnnotationsInstructionsContent agentId={agentId} experimentId={experimentId} />}
      position="bottom"
      popoverClassName="bg-gray-900 text-white rounded-[4px]"
    >
      <button
        onClick={() => {}}
        className="bg-white border border-gray-200 text-gray-900 hover:bg-gray-100 cursor-pointer px-2 py-1 rounded-[2px] h-8 flex items-center justify-center shadow-sm shadow-black/5"
        title="Improve your agents with annotations"
      >
        <div className="flex items-center gap-2 px-0.5">
          <Info size={12} />
          <span className="text-xs font-medium">Improve your agents with annotations</span>
        </div>
      </button>
    </HoverPopover>
  );
}
