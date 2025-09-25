import { memo } from "react";

interface CompletionTableBadgeCellProps {
  value: unknown;
  variant?: "default" | "success" | "warning" | "error" | "white";
  rounded?: "default" | "sm" | "md" | "lg" | "none" | string;
}

function CompletionTableBadgeCell({
  value,
  variant = "default",
  rounded = "md",
}: CompletionTableBadgeCellProps) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-400">N/A</span>;
  }

  const getVariantClasses = (variant: string) => {
    switch (variant) {
      case "success":
        return "bg-green-100 text-green-800 border-green-200";
      case "warning":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "error":
        return "bg-red-100 text-red-800 border-red-200";
      case "white":
        return "bg-white text-gray-800 border-gray-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const getRoundedClass = (rounded: string) => {
    switch (rounded) {
      case "none":
        return "";
      case "sm":
        return "rounded-sm";
      case "default":
        return "rounded";
      case "md":
        return "rounded-md";
      case "lg":
        return "rounded-lg";
      default:
        return `rounded-[${rounded}]`;
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-1 text-xs font-medium border w-fit max-w-full overflow-hidden text-ellipsis whitespace-nowrap ${getRoundedClass(rounded)} ${getVariantClasses(variant)}`}
    >
      {String(value)}
    </span>
  );
}

export default memo(CompletionTableBadgeCell);
