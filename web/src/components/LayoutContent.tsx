"use client";

import { useState } from "react";
import CommandPalette from "@/components/CommandPalette";
import NavigationSidebar from "@/components/sidebar/NavigationSidebar";
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut";

export default function LayoutContent({ children }: { children: React.ReactNode }) {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  useKeyboardShortcut(["mod", "k"], () => {
    setIsCommandPaletteOpen((prev) => !prev);
  });

  return (
    <>
      <div className="flex h-screen">
        <NavigationSidebar onOpenCommandPalette={() => setIsCommandPaletteOpen(true)} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
      <CommandPalette isOpen={isCommandPaletteOpen} onClose={() => setIsCommandPaletteOpen(false)} />
    </>
  );
}
