import { useMemo } from "react";
import { TextBreak } from "@/components/utils/TextBreak";
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
      <TextBreak className="text-xs text-gray-900 font-semibold">{value.title}</TextBreak>
      <div className="flex flex-col gap-0.5">
        {value.description && <TextBreak className="text-xs text-gray-500 line-clamp-2">{value.description}</TextBreak>}
        {strippedResult && <TextBreak className="text-xs text-gray-500 line-clamp-1">{strippedResult}</TextBreak>}
      </div>
    </div>
  );
}
