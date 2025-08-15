import { Tool } from "@/types/models";
import { ToolEntry } from "./ToolEntry";

interface AvailableToolsProps {
  tools?: Tool[];
}

export function AvailableTools({ tools }: AvailableToolsProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-[2px] py-2">
      <div className="text-xs font-medium text-gray-700 mb-2 pb-2 border-b border-gray-200 border-dashed px-2">
        Available Tools
      </div>
      {tools && tools.length > 0 ? (
        <div className="space-y-2 px-2">
          {tools.map((tool, index) => (
            <ToolEntry key={index} tool={tool} index={index} showSeparator={index < tools.length - 1} />
          ))}
        </div>
      ) : (
        <div className="text-xs text-gray-500 px-2">No tools available</div>
      )}
    </div>
  );
}
