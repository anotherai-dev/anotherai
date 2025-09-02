import { ModelIconWithName } from "@/components/ModelIcon";
import { formatDate } from "@/components/utils/utils";
import { Deployment } from "@/types/models";

interface DeploymentInfoSectionProps {
  deployment: Deployment;
}

export function DeploymentInfoSection({ deployment }: DeploymentInfoSectionProps) {
  const infoRows = [
    {
      label: "Agent ID",
      value: deployment.agent_id,
    },
    {
      label: "Model",
      value: (
        <ModelIconWithName modelId={deployment.version.model} size={12} nameClassName="text-[13px] text-gray-700" />
      ),
    },
    {
      label: "Created",
      value: formatDate(deployment.created_at, "relative_with_time"),
    },
  ];

  return (
    <div className="mb-8">
      <div className="bg-gray-50 border border-gray-200 rounded-[2px]">
        {infoRows.map((row, index) => (
          <div
            key={row.label}
            className={`flex items-center ${index < infoRows.length - 1 ? "border-b border-gray-100" : ""}`}
          >
            <div className="w-[250px] px-4 py-3 text-[13px] font-medium text-gray-700 border-r border-gray-100">
              {row.label}
            </div>
            <div className="flex-1 px-4 py-3 text-[13px] text-gray-700">{row.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
