interface ExperimentCellData {
  title: string;
  description: string;
  result?: string;
}

interface ExperimentsTableExperimentCellProps {
  value: ExperimentCellData;
}

export function ExperimentsTableExperimentCell({
  value,
}: ExperimentsTableExperimentCellProps) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <div className="text-xs text-gray-900 font-semibold break-words">
        {value.title}
      </div>
      {value.description && (
        <div className="text-xs text-gray-500 break-words line-clamp-2">
          {value.description}
        </div>
      )}
      {value.result && (
        <div className="text-xs text-blue-600 break-words line-clamp-1">
          Result: {value.result}
        </div>
      )}
    </div>
  );
}
