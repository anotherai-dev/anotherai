"use client";

import { Suspense, useState } from "react";
import CommandPalette from "@/components/CommandPalette";
import NavigationSidebar from "@/components/sidebar/NavigationSidebar";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";

interface LayoutContentProps {
  children: React.ReactNode;
  initialSidebarExpanded?: boolean;
}

export default function LayoutContent({ children, initialSidebarExpanded = true }: LayoutContentProps) {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  useKeyboardShortcut(["mod", "k"], () => {
    setIsCommandPaletteOpen((prev) => !prev);
  });

  return (
    <>
      <div className="flex h-screen">
        <Suspense fallback={<div className="w-64 bg-gray-50 border-r border-gray-200" />}>
          <NavigationSidebar
            onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
            initialExpanded={initialSidebarExpanded}
          />
        </Suspense>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
      <CommandPalette isOpen={isCommandPaletteOpen} onClose={() => setIsCommandPaletteOpen(false)} />
    </>
  );
}
