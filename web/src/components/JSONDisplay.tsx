import { cx } from "class-variance-authority";
import { ReactNode } from "react";

type JSONDisplayProps = {
  value: unknown;
  variant?: "default" | "compact" | "minimal";
  maxLength?: number;
  maxHeight?: string;
  className?: string;
  onClick?: () => void;
  children?: ReactNode;
};

export function JSONDisplay({
  value,
  variant = "default",
  maxLength,
  maxHeight = "300px",
  className,
  onClick,
  children,
}: JSONDisplayProps) {
  const jsonString = JSON.stringify(value, null, 2);
  const displayText = maxLength ? `${jsonString.substring(0, maxLength)}...` : jsonString;

  const baseClasses = "whitespace-pre-wrap break-words font-mono";
  const scrollClasses = maxHeight ? "overflow-y-auto" : "";

  const variantClasses = {
    default: "text-xs text-gray-900 bg-gray-50 p-2 rounded border",
    compact: "text-[11px] text-gray-900 bg-white border border-gray-200 rounded-[2px] px-2 py-1 font-normal",
    minimal: "text-xs text-gray-600",
  };

  const Component = variant === "minimal" ? "span" : "pre";
  const heightStyle = maxHeight ? { maxHeight } : undefined;

  return (
    <Component
      className={cx(baseClasses, variantClasses[variant], scrollClasses, className)}
      style={heightStyle}
      onClick={onClick}
    >
      {displayText}
      {children}
    </Component>
  );
}
