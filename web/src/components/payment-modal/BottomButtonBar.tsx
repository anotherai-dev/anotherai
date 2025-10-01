"use client";

import { HoverPopover } from "@/components/HoverPopover";

interface BottomButtonBarProps {
  tooltipText?: string;
  actionText: string;
  isActionDisabled: boolean;
  onCancel: () => void;
  onAction: (() => void) | (() => Promise<void>) | undefined;
  type?: "submit" | "button";
}

export function BottomButtonBar({
  isActionDisabled,
  onCancel,
  onAction,
  tooltipText,
  actionText,
  type,
}: BottomButtonBarProps) {
  return (
    <div className="flex flex-row gap-2 items-center justify-between px-4 py-3 border-t border-gray-200">
      <button
        className="px-4 py-2 bg-gray-200 text-gray-700 text-[13px] font-semibold rounded-[2px] hover:bg-gray-300 transition-colors cursor-pointer"
        onClick={onCancel}
      >
        Cancel
      </button>

      {tooltipText ? (
        <HoverPopover content={tooltipText} position="top" delay={100}>
          <div>
            <button
              type={type}
              className={`px-4 py-2 text-[13px] font-medium rounded-[2px] transition-colors cursor-pointer ${
                isActionDisabled
                  ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
              }`}
              disabled={isActionDisabled}
              onClick={onAction}
            >
              {actionText}
            </button>
          </div>
        </HoverPopover>
      ) : (
        <button
          type={type}
          className={`px-4 py-2 text-[13px] font-medium rounded-[2px] transition-colors cursor-pointer ${
            isActionDisabled
              ? "bg-gray-200 text-gray-400 cursor-not-allowed"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          }`}
          disabled={isActionDisabled}
          onClick={onAction}
        >
          {actionText}
        </button>
      )}
    </div>
  );
}
