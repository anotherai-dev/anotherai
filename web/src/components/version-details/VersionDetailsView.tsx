import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { SchemaViewer } from "@/components/SchemaViewer";
import { MessagesViewer } from "@/components/messages/MessagesViewer";
import { getVersionWithDefaults } from "@/components/utils/utils";
import { Version } from "@/types/models";
import { AvailableTools } from "./AvailableTools";

type VersionDetailsViewProps = {
  version: Version;
  showPrompt?: boolean;
  showOutputSchema?: boolean;
};

export function VersionDetailsView({
  version,
  showPrompt = false,
  showOutputSchema = false,
}: VersionDetailsViewProps) {
  const extendedVersion = getVersionWithDefaults(version);
  const [isAdvancedExpanded, setIsAdvancedExpanded] = useState(false);

  return (
    <div className="w-full space-y-2 py-1">
      {/* Model */}
      <div className="bg-white border border-gray-200 rounded-[2px] p-2">
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-gray-700">Model</span>
          <span className="text-xs text-gray-900">{version.model}</span>
        </div>
      </div>

      {/* Temperature */}
      <div className="bg-white border border-gray-200 rounded-[2px] p-2">
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-gray-700">Temperature</span>
          <span className="text-xs text-gray-900">{version.temperature}</span>
        </div>
      </div>

      {/* Top P */}
      <div className="bg-white border border-gray-200 rounded-[2px] p-2">
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-gray-700">Top P</span>
          <span className="text-xs text-gray-900">{version.top_p}</span>
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="bg-white border border-gray-200 rounded-[2px]">
        <button
          onClick={() => setIsAdvancedExpanded(!isAdvancedExpanded)}
          className="w-full p-2 flex items-center justify-between hover:bg-gray-50 transition-colors"
        >
          <span className="text-xs font-medium text-gray-700">
            Advanced Settings
          </span>
          {isAdvancedExpanded ? (
            <ChevronDown className="w-3 h-3 text-gray-500" />
          ) : (
            <ChevronRight className="w-3 h-3 text-gray-500" />
          )}
        </button>
        {isAdvancedExpanded && (
          <div className="border-t border-gray-200 p-2 space-y-2">
            {/* Use Cache */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Use Cache</span>
              <span className="text-xs text-gray-900">
                {extendedVersion.use_cache}
              </span>
            </div>

            {/* Max Tokens */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Max Tokens</span>
              <span className="text-xs text-gray-900 ">
                {extendedVersion.max_tokens}
              </span>
            </div>

            {/* Stream */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Stream</span>
              <span className="text-xs text-gray-900 ">
                {extendedVersion.stream ? "true" : "false"}
              </span>
            </div>

            {/* Include Usage */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Include Usage</span>
              <span className="text-xs text-gray-900 ">
                {extendedVersion.include_usage ? "true" : "false"}
              </span>
            </div>

            {/* Presence Penalty */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Presence Penalty</span>
              <span className="text-xs text-gray-900 ">
                {extendedVersion.presence_penalty}
              </span>
            </div>

            {/* Frequency Penalty */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Frequency Penalty</span>
              <span className="text-xs text-gray-900 ">
                {extendedVersion.frequency_penalty}
              </span>
            </div>

            {/* Stop */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Stop</span>
              <span className="text-xs text-gray-900 ">
                {Array.isArray(extendedVersion.stop)
                  ? extendedVersion.stop.join(", ")
                  : extendedVersion.stop}
              </span>
            </div>

            {/* Tool Choice */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">Tool Choice</span>
              <span className="text-xs text-gray-900 ">
                {typeof extendedVersion.tool_choice === "string"
                  ? extendedVersion.tool_choice
                  : JSON.stringify(extendedVersion.tool_choice)}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Prompt */}
      {showPrompt && version.prompt && version.prompt.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-[2px] p-2">
          <div className="text-xs font-medium text-gray-700 mb-2">Prompt</div>
          <MessagesViewer messages={version.prompt} />
        </div>
      )}

      {/* Available Tools */}
      <AvailableTools tools={version.tools} />

      {/* Output Schema */}
      {showOutputSchema && version.output_schema && (
        <div className="bg-white border border-gray-200 rounded-[2px] p-2">
          <div className="text-xs font-medium text-gray-700 mb-2">
            Output Schema
          </div>
          <SchemaViewer schema={version.output_schema} />
        </div>
      )}
    </div>
  );
}
