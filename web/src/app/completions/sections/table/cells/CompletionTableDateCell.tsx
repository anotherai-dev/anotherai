import { useMemo } from "react";
import { formatDate } from "@/components/utils/utils";

interface CompletionTableDateCellProps {
  value: unknown;
  format?: "date" | "datetime" | "time" | "relative" | "relative_with_time";
}

export function CompletionTableDateCell({ value, format = "date" }: CompletionTableDateCellProps) {
  const formattedDate = useMemo(() => formatDate(value, format), [value, format]);
  
  if (formattedDate === "N/A" || formattedDate === "Invalid Date") {
    return <span className="text-xs text-gray-400">{formattedDate}</span>;
  }

  return <span className="text-xs text-gray-800">{formattedDate}</span>;
}
