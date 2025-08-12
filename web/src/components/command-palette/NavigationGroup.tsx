import { Command } from "cmdk";
import React from "react";
import { CommandPaletteItem } from "./CommandPaletteItem";

interface NavigationItem {
  id: string;
  name: string;
  description: string;
  href: string;
  icon: () => React.JSX.Element;
  keywords: string[];
}

interface NavigationGroupProps {
  items: NavigationItem[];
  onSelect: (value: string) => void;
}

export function NavigationGroup({ items, onSelect }: NavigationGroupProps) {
  return (
    <Command.Group heading="Navigation">
      {items.map((item) => (
        <CommandPaletteItem
          key={item.id}
          value={`nav:${item.id} ${item.name} ${item.description} ${item.keywords.join(" ")}`}
          onSelect={() => onSelect(`nav:${item.id}`)}
          icon={<item.icon />}
          title={item.name}
          subtitle={item.description}
        />
      ))}
    </Command.Group>
  );
}
