import { cx } from "class-variance-authority";
import { memo } from "react";
import { SchemaViewer } from "@/components/SchemaViewer";
import { OutputSchema } from "@/types/models";

interface CompletionOutputSchemaCellProps {
  value: unknown;
  maxWidth?: string;
  sharedKeypathsOfSchemas?: string[];
}

function CompletionOutputSchemaCell({
  value,
  maxWidth = "max-w-xs",
  sharedKeypathsOfSchemas,
}: CompletionOutputSchemaCellProps) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-gray-400">N/A</span>;
  }

  if (typeof value === "object" && value !== null) {
    const obj = value as Record<string, unknown>;

    // Check if it has the expected OutputSchema structure
    if (obj.json_schema && typeof obj.json_schema === "object") {
      return (
        <div className={cx("max-h-full overflow-y-auto", maxWidth)}>
          <SchemaViewer
            schema={obj as unknown as OutputSchema}
            sharedKeypathsOfSchemas={sharedKeypathsOfSchemas}
            className="text-xs"
          />
        </div>
      );
    }
  }

  // Fallback for unexpected format
  return (
    <div className={cx("text-xs text-gray-600 overflow-hidden", maxWidth)}>
      <pre className="whitespace-pre-wrap">{JSON.stringify(value, null, 2).substring(0, 200)}...</pre>
    </div>
  );
}

// Helper function to compare string arrays for memoization
function areStringArraysEqual(prev?: string[], next?: string[]): boolean {
  if (prev === next) return true;
  if (!prev || !next) return false;
  if (prev.length !== next.length) return false;

  for (let i = 0; i < prev.length; i++) {
    if (prev[i] !== next[i]) {
      return false;
    }
  }
  return true;
}

export default memo(CompletionOutputSchemaCell, (prevProps, nextProps) => {
  return (
    prevProps.value === nextProps.value &&
    prevProps.maxWidth === nextProps.maxWidth &&
    areStringArraysEqual(prevProps.sharedKeypathsOfSchemas, nextProps.sharedKeypathsOfSchemas)
  );
});
