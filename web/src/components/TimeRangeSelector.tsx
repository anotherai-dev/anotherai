"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown, Clock } from "lucide-react";
import { useState } from "react";

export type TimeRangeOption = {
  value: string;
  label: string;
  days: number;
};

export const TIME_RANGE_OPTIONS: TimeRangeOption[] = [
  { value: "24h", label: "Last 24 hours", days: 1 },
  { value: "7d", label: "Last 7 days", days: 7 },
  { value: "30d", label: "Last 30 days", days: 30 },
  { value: "90d", label: "Last 90 days", days: 90 },
];

interface TimeRangeSelectorProps {
  selectedRange?: TimeRangeOption;
  onRangeChange?: (range: TimeRangeOption) => void;
  className?: string;
}

export function TimeRangeSelector({
  selectedRange = TIME_RANGE_OPTIONS[1], // Default to "Last 7 days"
  onRangeChange,
  className = "",
}: TimeRangeSelectorProps) {
  const [open, setOpen] = useState(false);

  const handleRangeSelect = (range: TimeRangeOption) => {
    onRangeChange?.(range);
    setOpen(false);
  };

  return (
    <div className={`flex items-center ${className}`}>
      <DropdownMenu.Root open={open} onOpenChange={setOpen}>
        <DropdownMenu.Trigger asChild>
          <button className="flex items-center gap-2 px-3 py-2 text-[13px] font-medium text-gray-700 bg-white border border-gray-200 rounded-[2px] hover:bg-gray-50 focus:outline-none cursor-pointer shadow-sm shadow-black/5">
            <Clock size={14} />
            <span>{selectedRange.label}</span>
            <ChevronDown size={12} className={`transition-transform ${open ? "rotate-180" : ""}`} />
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            className="z-[9999] bg-white border border-gray-200 rounded-[2px] shadow-lg py-1 px-1 min-w-[160px]"
            sideOffset={4}
            align="end"
          >
            {TIME_RANGE_OPTIONS.map((option) => (
              <DropdownMenu.Item key={option.value} asChild>
                <button
                  onClick={() => handleRangeSelect(option)}
                  className={`w-full px-3 py-2 text-[13px] text-left rounded-[2px] hover:bg-gray-100 focus:outline-none cursor-pointer ${
                    selectedRange.value === option.value ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700"
                  }`}
                >
                  {option.label}
                </button>
              </DropdownMenu.Item>
            ))}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>
  );
}
