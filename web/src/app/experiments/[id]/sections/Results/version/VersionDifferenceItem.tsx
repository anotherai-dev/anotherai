import { ChevronDown, ChevronRight } from "lucide-react";
import React, { useMemo, useState } from "react";
import { JSONDisplay } from "@/components/JSONDisplay";
import { createOutputSchemaFromJSON, isJSONSchema, parseJSONValue } from "@/components/utils/utils";
import { VersionSchemaSection } from "./VersionSchemaSection";

type VersionDifferenceItemProps = {
  keyName: string;
  value: unknown;
  onClick?: (e?: React.MouseEvent) => void;
};

export function VersionDifferenceItem({ keyName, value, onClick }: VersionDifferenceItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const parsedJSON = useMemo(() => parseJSONValue(value), [value]);
  const isSchemaDetected = useMemo(() => isJSONSchema(parsedJSON), [parsedJSON]);

  // Memoized OutputSchema creation for JSON schemas
  const outputSchema = useMemo(() => {
    return isSchemaDetected ? createOutputSchemaFromJSON(parsedJSON, keyName || "detected-schema") : null;
  }, [isSchemaDetected, parsedJSON, keyName]);

  const handleToggle = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  // If it's a JSON schema, use VersionSchemaSection with collapse/expand
  if (outputSchema) {
    return (
      <div className="px-2 py-1 text-xs rounded font-medium bg-gray-100 border border-gray-200 text-gray-700 w-full hover:bg-gray-200/50 cursor-pointer transition-colors">
        <div className="flex items-center justify-between" onClick={handleToggle}>
          <span className="text-gray-500 capitalize">{keyName}</span>
          <div className="text-gray-500">{isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</div>
        </div>
        {isExpanded && (
          <div className="mt-1" onClick={onClick}>
            <VersionSchemaSection outputSchema={outputSchema} className="" showAnnotations={false} />
          </div>
        )}
      </div>
    );
  }

  // If it's JSON (but not a schema), display it with formatting and collapse/expand
  if (parsedJSON !== null) {
    return (
      <div className="px-2 py-1 text-xs rounded font-medium bg-gray-100 border border-gray-200 text-gray-700 w-full hover:bg-gray-200/50 cursor-pointer transition-colors">
        <div className="flex items-center justify-between" onClick={handleToggle}>
          <span className="text-gray-500 capitalize">{keyName}</span>
          <div className="text-gray-500">{isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</div>
        </div>
        {isExpanded && (
          <div className="mt-1" onClick={onClick}>
            <JSONDisplay value={parsedJSON} variant="compact" />
          </div>
        )}
      </div>
    );
  }

  // Default layout for non-JSON values
  return (
    <div
      className="flex items-center justify-between px-2 py-1 text-xs rounded font-medium bg-gray-100 border border-gray-200 text-gray-700 w-full hover:bg-gray-200/50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <span className="text-gray-500 capitalize">{keyName}</span>
      <span className="font-semibold">{String(value)}</span>
    </div>
  );
}
