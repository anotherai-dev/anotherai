interface Props {
  value: unknown;
}

export function CompletionBaseTableCell(props: Props) {
  const { value } = props;

  if (value === null || value === undefined) {
    return <div className="text-xs text-gray-400">N/A</div>;
  }

  return (
    <div className="flex text-xs text-gray-800 overflow-y-auto">
      {String(value)}
    </div>
  );
}
