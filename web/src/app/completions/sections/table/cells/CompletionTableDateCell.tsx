interface CompletionTableDateCellProps {
  value: unknown;
  format?: "date" | "datetime" | "time" | "relative";
}

export function CompletionTableDateCell({
  value,
  format = "date",
}: CompletionTableDateCellProps) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-400">N/A</span>;
  }

  const date = new Date(String(value));

  if (isNaN(date.getTime())) {
    return <span className="text-xs text-gray-400">Invalid Date</span>;
  }

  const formatDate = (date: Date, format: string) => {
    switch (format) {
      case "datetime":
        return date.toLocaleString();
      case "time":
        return date.toLocaleTimeString();
      case "relative":
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return "Just now";
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
      default:
        return date.toLocaleDateString();
    }
  };

  return (
    <span className="text-xs text-gray-800">{formatDate(date, format)}</span>
  );
}
