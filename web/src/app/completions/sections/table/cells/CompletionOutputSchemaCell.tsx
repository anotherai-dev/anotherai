import { cx } from "class-variance-authority";
import { JSONDisplay } from "@/components/JSONDisplay";
import { SchemaViewer } from "@/components/SchemaViewer";
import { OutputSchema } from "@/types/models";

interface CompletionOutputSchemaCellProps {
  value: unknown;
  maxWidth?: string;
  sharedKeypathsOfSchemas?: string[];
}

export function CompletionOutputSchemaCell({
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
    <div className={cx("overflow-hidden", maxWidth)}>
      <JSONDisplay value={value} variant="minimal" maxLength={200} />
    </div>
  );
}
