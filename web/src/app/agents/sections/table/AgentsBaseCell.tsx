interface AgentsBaseCellProps {
  value: unknown;
  formatter?: (value: unknown) => string;
}

export function AgentsBaseCell({ value, formatter }: AgentsBaseCellProps) {
  const displayValue = formatter
    ? formatter(value)
    : value === null || value === undefined || value === ""
      ? "-"
      : String(value);

  return <span className="text-xs text-gray-500">{displayValue}</span>;
}
