import { TextBreak } from "@/components/utils/TextBreak";
import { CompletionTableBadgeCell } from "./CompletionTableBadgeCell";

interface CompletionTableMetadataCellProps {
  value: unknown;
}

export function CompletionTableMetadataCell({ value }: CompletionTableMetadataCellProps) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-400">N/A</span>;
  }

  if (typeof value !== "object" || value === null) {
    return <span className="text-xs text-gray-600">{String(value)}</span>;
  }

  const metadata = value as Record<string, unknown>;
  const entries = Object.entries(metadata);

  if (entries.length === 0) {
    return <span className="text-xs text-gray-400">Empty</span>;
  }

  return (
    <div className="space-y-2">
      {entries.map(([key, val]) => {
        const displayKey = key.startsWith("workflowai.") ? key.slice("workflowai.".length) : key;
        return (
          <div key={key} className="space-y-1">
            <TextBreak className="text-xs text-gray-600">{displayKey}</TextBreak>
            <CompletionTableBadgeCell value={String(val)} variant="white" rounded="2px" />
          </div>
        );
      })}
    </div>
  );
}
