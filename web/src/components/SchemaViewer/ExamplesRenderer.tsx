interface ExamplesRendererProps {
  examples: unknown[];
  showExamples: boolean;
  variant?: "default" | "object-header";
}

export function ExamplesRenderer({ examples, showExamples, variant = "default" }: ExamplesRendererProps) {
  if (!showExamples || !examples || examples.length === 0) {
    return null;
  }

  const backgroundClass = variant === "object-header" ? "bg-white" : "bg-gray-50";

  return (
    <div className="text-xs text-gray-600 mt-1">
      <div className="font-medium mb-0.5">Examples:</div>
      <div className="flex flex-wrap gap-1">
        {examples.map((example, index) => (
          <span
            key={index}
            className={`inline-block ${backgroundClass} border border-gray-200 px-1.5 py-0.5 rounded text-gray-800`}
          >
            {JSON.stringify(example)}
          </span>
        ))}
      </div>
    </div>
  );
}
