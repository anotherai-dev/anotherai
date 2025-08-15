"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";

interface DropdownMenuProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  align?: "start" | "center" | "end";
  sideOffset?: number;
  onOpenChange?: (open: boolean) => void;
}

export default function PopoverMenu({
  trigger,
  children,
  className = "z-[9999] bg-white border border-gray-200 rounded-md shadow-lg py-1 px-1 min-w-[120px]",
  align = "center",
  sideOffset = 4,
  onOpenChange,
}: DropdownMenuProps) {
  return (
    <DropdownMenu.Root onOpenChange={onOpenChange}>
      <DropdownMenu.Trigger asChild>{trigger}</DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content className={className} sideOffset={sideOffset} align={align}>
          {children}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
