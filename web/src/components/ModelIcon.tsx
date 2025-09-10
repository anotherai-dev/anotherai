import Image from "next/image";
import { useState } from "react";
import { useOrFetchModels } from "@/store/models";

interface ModelIconProps {
  modelId: string;
  className?: string;
  size?: number;
}

export function ModelIcon({ modelId, className = "", size = 12 }: ModelIconProps) {
  const { getModelById } = useOrFetchModels();
  const [imageError, setImageError] = useState(false);

  const model = getModelById(modelId);

  // Don't render anything if no model data, image failed to load, or no icon URL
  if (!model || imageError || !model.icon_url) {
    return null;
  }

  return (
    <Image
      src={model.icon_url}
      alt={`${model.display_name} icon`}
      className={`rounded-sm ${className}`}
      width={size}
      height={size}
      title={model.display_name}
      onError={() => setImageError(true)}
      onLoad={() => setImageError(false)}
      unoptimized // Since these are external SVG URLs from blob storage
    />
  );
}

interface ModelIconWithNameProps extends ModelIconProps {
  showName?: boolean;
  nameClassName?: string;
  reasoningEffort?: "disabled" | "low" | "medium" | "high";
  reasoningBudget?: number;
}

export function ModelIconWithName({
  modelId,
  className = "",
  size = 12,
  showName = true,
  nameClassName = "text-sm text-gray-900",
  reasoningEffort,
  reasoningBudget,
}: ModelIconWithNameProps) {
  const { getModelById } = useOrFetchModels();
  const [imageError, setImageError] = useState(false);

  const model = getModelById(modelId);

  // Check if we should show the icon
  const shouldShowIcon = model && !imageError && model.icon_url;

  // Format reasoning effort display
  const reasoningDisplay = reasoningEffort ? reasoningEffort : reasoningBudget?.toString();

  return (
    <div className={`flex items-start ${shouldShowIcon ? "gap-1.5" : ""}`}>
      {shouldShowIcon && (
        <Image
          src={model.icon_url}
          alt={`${model.display_name} icon`}
          className={`rounded-sm mt-0.5 ${className}`}
          width={size}
          height={size}
          title={model.display_name}
          onError={() => setImageError(true)}
          onLoad={() => setImageError(false)}
          unoptimized // Since these are external SVG URLs from blob storage
        />
      )}
      {showName && (
        <div className="flex items-center gap-1">
          <span className={nameClassName}>{model?.display_name || modelId}</span>
          {reasoningDisplay && (
            <span className="text-xs text-gray-500 bg-gray-100 border border-gray-200 px-1.5 py-0.5 rounded-[2px]">
              {reasoningDisplay}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
