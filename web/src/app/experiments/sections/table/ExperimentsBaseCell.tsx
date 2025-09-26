import { memo } from "react";

interface ExperimentsBaseCellProps {
  value: unknown;
  formatter?: (value: unknown) => string;
}

function ExperimentsBaseCell({ value, formatter }: ExperimentsBaseCellProps) {
  const displayValue = formatter
    ? formatter(value)
    : value === null || value === undefined || value === ""
      ? "-"
      : String(value);

  return <span className="text-xs text-gray-500">{displayValue}</span>;
}

export default memo(ExperimentsBaseCell);
