import { Command } from "cmdk";
import { BarChart3, Table } from "lucide-react";
import { View } from "@/types/models";
import { CommandPaletteItem } from "./CommandPaletteItem";

interface ViewFolder {
  name: string;
  views: View[];
}

interface ViewsGroupProps {
  viewsBySection: Record<string, ViewFolder>;
  onSelect: (value: string) => void;
}

export function ViewsGroup({ viewsBySection, onSelect }: ViewsGroupProps) {
  const entries = Object.entries(viewsBySection);

  if (entries.length === 0) return null;

  const isChart = (view: View) => {
    return (
      view.graph && ["bar", "line", "pie", "scatter"].includes(view.graph.type)
    );
  };

  const getViewType = (view: View) => {
    if (isChart(view)) return "Chart";
    if (view.graph?.type === "table") return "Table";
    return "Query";
  };

  return (
    <Command.Group heading="Views">
      {entries
        .sort(([, a], [, b]) => a.name.localeCompare(b.name))
        .flatMap(([, folderData]) =>
          folderData.views.map((view) => {
            const viewType = getViewType(view);
            return (
              <CommandPaletteItem
                key={view.id}
                value={`view:${view.id} ${view.title} ${folderData.name} ${viewType.toLowerCase()}`}
                onSelect={() => onSelect(`view:${view.id}`)}
                icon={
                  view.graph?.type === "table" ? (
                    <Table className="w-4 h-4 text-gray-500" />
                  ) : (
                    <BarChart3 className="w-4 h-4 text-gray-500" />
                  )
                }
                title={view.title}
                subtitle={`${folderData.name} • ${viewType}`}
              />
            );
          })
        )}
    </Command.Group>
  );
}
