import { Copy } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { SchemaViewer } from "@/components/SchemaViewer";
import { useToast } from "@/components/ToastProvider";
import {
  createOutputSchemaFromJSON,
  getVersionKeyDisplayName,
  isJSONSchema,
  parseJSONValue,
} from "@/components/utils/utils";

type VersionDetailsRowProps = {
  keyName: string;
  value: unknown;
  showExamples?: boolean;
};

export function VersionDetailsRow({ keyName, value, showExamples = false }: VersionDetailsRowProps) {
  const displayName = getVersionKeyDisplayName(keyName);
  const parsedJSON = parseJSONValue(value);
  const isSchema = useMemo(() => isJSONSchema(parsedJSON), [parsedJSON]);
  const [isHovered, setIsHovered] = useState(false);
  const { showToast } = useToast();

  // Memoized OutputSchema creation for JSON schemas
  const outputSchema = useMemo(() => {
    return isSchema ? createOutputSchemaFromJSON(parsedJSON, keyName || "detected-schema") : null;
  }, [isSchema, parsedJSON, keyName]);

  const copySchemaContent = useCallback(async () => {
    const textToCopy = JSON.stringify(outputSchema?.json_schema || parsedJSON, null, 2);

    try {
      await navigator.clipboard.writeText(textToCopy);
      showToast("Copied schema content");
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
      showToast("Failed to copy");
    }
  }, [outputSchema, parsedJSON, showToast]);

  // Handle different value types
  const renderValue = () => {
    // JSON Schema case
    if (outputSchema) {
      return (
        <div className="mt-2 relative" onMouseEnter={() => setIsHovered(true)} onMouseLeave={() => setIsHovered(false)}>
          <SchemaViewer schema={outputSchema} showDescriptions={true} showExamples={showExamples} />
          {isHovered && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                copySchemaContent();
              }}
              className="absolute top-1 right-1 p-1 bg-white border border-gray-200 rounded-[2px] hover:bg-gray-100 transition-colors cursor-pointer z-10"
              title="Copy schema content"
            >
              <Copy size={12} />
            </button>
          )}
        </div>
      );
    }

    // JSON case (but not schema)
    if (parsedJSON !== null) {
      return (
        <pre className="text-xs text-gray-900 whitespace-pre-wrap break-words font-mono bg-gray-50 p-2 rounded border">
          {JSON.stringify(parsedJSON, null, 2)}
        </pre>
      );
    }

    // Array case
    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-xs text-gray-900">Empty array</span>;
      return <span className="text-xs text-gray-900">{JSON.stringify(value)}</span>;
    }

    // Object case
    if (value && typeof value === "object") {
      return (
        <pre className="text-xs text-gray-900 whitespace-pre-wrap break-words font-mono bg-gray-50 p-2 rounded border">
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }

    // Primitive values
    return (
      <span className="text-xs text-gray-900">{value === null || value === undefined ? "null" : String(value)}</span>
    );
  };

  return (
    <div className="bg-white border border-gray-200 rounded-[2px] p-2">
      {outputSchema || (parsedJSON !== null && typeof parsedJSON === "object") ? (
        // Header-style layout for schemas and complex JSON
        <>
          <div className="text-xs font-medium text-gray-700 mb-2">{displayName}</div>
          {renderValue()}
        </>
      ) : (
        // Side-by-side layout for simple values
        <div className="flex justify-between items-center">
          <span className="text-xs font-medium text-gray-700">{displayName}</span>
          {renderValue()}
        </div>
      )}
    </div>
  );
}
