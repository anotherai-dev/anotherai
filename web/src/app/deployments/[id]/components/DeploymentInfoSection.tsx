import { ChevronDown, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { formatDate, getVersionKeyDisplayName, getVersionWithDefaults } from "@/components/utils/utils";
import { Deployment } from "@/types/models";
import { DeploymentTableRows } from "./DeploymentTableRows";
import { renderValue } from "./renderValue";

interface DeploymentInfoSectionProps {
  deployment: Deployment;
}

export function DeploymentInfoSection({ deployment }: DeploymentInfoSectionProps) {
  const [isAdvancedExpanded, setIsAdvancedExpanded] = useState(false);

  const versionWithDefaults = useMemo(() => {
    return getVersionWithDefaults(deployment.version);
  }, [deployment.version]);

  const { basicVersionKeys, advancedKeys, complexKeys } = useMemo(() => {
    const basic = ["model", "temperature", "top_p"];
    const advanced = [
      "use_cache",
      "max_tokens",
      "stream",
      "include_usage",
      "presence_penalty",
      "frequency_penalty",
      "stop",
      "tool_choice",
    ];
    const complex = ["prompt", "tools", "output_schema"];

    const allKeys = Object.keys(versionWithDefaults);
    const availableKeys = allKeys.filter((key) => !["id"].includes(key));

    return {
      basicVersionKeys: basic.filter((key) => availableKeys.includes(key)),
      advancedKeys: advanced.filter((key) => availableKeys.includes(key)),
      complexKeys: complex.filter((key) => availableKeys.includes(key)),
    };
  }, [versionWithDefaults]);

  const deploymentRows = useMemo(
    () => [
      {
        label: "Deployment ID",
        value: deployment.id,
        copyValue: `anotherai/deployment/${deployment.id}`,
        copyLabel: "Deployment ID",
      },
      {
        label: "Agent ID",
        value: deployment.agent_id,
        copyValue: `anotherai/agent/${deployment.agent_id}`,
        copyLabel: "Agent ID",
      },
      {
        label: "Version ID",
        value: deployment.version.id,
        copyValue: `anotherai/version/${deployment.version.id}`,
        copyLabel: "Version ID",
      },
      {
        label: "Created",
        value: formatDate(deployment.created_at, "relative_with_time"),
      },
    ],
    [deployment.id, deployment.agent_id, deployment.version.id, deployment.created_at]
  );

  const basicVersionRows = useMemo(
    () =>
      basicVersionKeys.map((key) => ({
        label: getVersionKeyDisplayName(key),
        value: renderValue(key, (versionWithDefaults as unknown as Record<string, unknown>)[key]),
      })),
    [basicVersionKeys, versionWithDefaults]
  );

  const complexVersionRows = useMemo(
    () =>
      complexKeys.map((key) => ({
        label: getVersionKeyDisplayName(key),
        value: renderValue(key, (versionWithDefaults as unknown as Record<string, unknown>)[key]),
      })),
    [complexKeys, versionWithDefaults]
  );

  return (
    <div className="mb-8">
      <div className="bg-gray-50 border border-gray-200 rounded-[2px]">
        {/* Deployment info */}
        <DeploymentTableRows rows={deploymentRows} />

        {/* Basic version settings */}
        <DeploymentTableRows rows={basicVersionRows} />

        {/* Advanced Settings collapsible */}
        <div className="flex border-b border-gray-100">
          <div className="w-full px-4 py-3 text-[13px] font-medium text-gray-700 flex items-start">
            <button
              onClick={() => setIsAdvancedExpanded(!isAdvancedExpanded)}
              className="flex items-center gap-1 hover:text-gray-900 transition-colors cursor-pointer"
            >
              <span>Advanced Settings</span>
              {isAdvancedExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
          </div>
        </div>

        {/* Advanced settings rows */}
        {isAdvancedExpanded && (
          <DeploymentTableRows
            rows={advancedKeys.map((key) => ({
              label: getVersionKeyDisplayName(key),
              value: renderValue(key, (versionWithDefaults as unknown as Record<string, unknown>)[key]),
            }))}
          />
        )}

        {/* Complex content */}
        <DeploymentTableRows rows={complexVersionRows} isLast={true} />
      </div>
    </div>
  );
}
