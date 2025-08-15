import { Command } from "cmdk";
import { ReactNode } from "react";

interface CommandPaletteItemProps {
  value: string;
  onSelect: () => void;
  icon: ReactNode;
  title: string;
  subtitle?: string;
}

export function CommandPaletteItem({ value, onSelect, icon, title, subtitle }: CommandPaletteItemProps) {
  return (
    <Command.Item
      value={value}
      onSelect={onSelect}
      className="flex items-center gap-3 px-3 py-2 text-sm rounded-md cursor-pointer hover:bg-gray-100 aria-selected:bg-gray-100"
    >
      {icon}
      <div className="flex-1">
        <div className="font-medium">{title}</div>
        {subtitle && <div className="text-xs text-gray-500">{subtitle}</div>}
      </div>
    </Command.Item>
  );
}
