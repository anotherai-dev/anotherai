import { useMemo } from "react";
import { stripMarkdown } from "@/components/utils/utils";

interface ExperimentCellData {
  title: string;
  description: string;
  result?: string;
}

interface ExperimentsTableExperimentCellProps {
  value: ExperimentCellData;
}

export function ExperimentsTableExperimentCell({ value }: ExperimentsTableExperimentCellProps) {
  const strippedResult = useMemo(() => {
    return value.result ? stripMarkdown(value.result) : null;
  }, [value.result]);

  return (
    <div className="flex flex-col gap-1 min-w-0">
      <div className="text-xs text-gray-900 font-semibold break-words">{value.title}</div>
      <div className="flex flex-col gap-0.5">
        {value.description && <div className="text-xs text-gray-500 break-words line-clamp-2">{value.description}</div>}
        {strippedResult && <div className="text-xs text-gray-500 break-words line-clamp-1">{strippedResult}</div>}
      </div>
    </div>
  );
}
