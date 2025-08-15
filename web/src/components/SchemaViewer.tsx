import React from "react";
import { Annotation, OutputSchema } from "@/types/models";
import { HoverContainer } from "./VariablesViewer/HoverContainer";

type SchemaViewerProps = {
  schema: OutputSchema;
  showDescriptions?: boolean;
  className?: string;
  sharedKeypathsOfSchemas?: string[];
  annotations?: Annotation[];
  annotationPrefix?: string;
  onKeypathSelect?: (keyPath: string) => void;
};

type JsonSchemaNode = {
  type?: string | string[];
  properties?: Record<string, JsonSchemaNode>;
  items?: JsonSchemaNode;
  required?: string[];
  description?: string;
  enum?: unknown[];
  default?: unknown;
};

export function SchemaViewer(props: SchemaViewerProps) {
  const {
    schema,
    showDescriptions = false,
    className = "",
    sharedKeypathsOfSchemas,
    annotations,
    annotationPrefix,
    onKeypathSelect,
  } = props;

  const renderTypeBadge = (type: string | string[] | undefined) => {
    if (!type) return null;

    const typeString = Array.isArray(type) ? type.join(" | ") : type;
    return (
      <span className="inline-block px-2 py-1 text-xs font-medium bg-white border border-gray-200 text-gray-800 rounded-[2px]">
        {typeString}
      </span>
    );
  };

  const renderProperty = (key: string, node: JsonSchemaNode, path: string): React.ReactElement => {
    // Clean up path to avoid double dots
    const cleanPath = path.replace(/\.$/, ""); // Remove trailing dot
    const currentPath = cleanPath === "" ? key : `${cleanPath}.${key}`;
    const isShared = !sharedKeypathsOfSchemas || sharedKeypathsOfSchemas.includes(currentPath);

    const renderPropertyName = (propertyName: string) => {
      // If sharedKeypathsOfSchemas is undefined, don't use coloring mode
      if (sharedKeypathsOfSchemas === undefined || isShared) {
        return <span className="text-xs font-medium text-gray-900">{propertyName}</span>;
      } else {
        return (
          <span className="inline-block px-2 py-1 text-xs font-medium bg-blue-100 border border-blue-300 text-blue-900 rounded-[2px]">
            {propertyName}
          </span>
        );
      }
    };

    // For objects, wrap the whole object and its properties in a rectangle
    if ((node.type === "object" || node.properties) && node.properties) {
      // For object headers, always show without badge since we're showing the structure, not the content
      const objectHeaderName = key || "Object";
      return (
        <div key={key} className="border border-gray-200 rounded-[2px] mb-3 w-fit">
          <div className="px-3 py-2 bg-gray-100 rounded-t-[2px] border-b border-gray-200">
            <span className="text-xs font-medium text-gray-900">{objectHeaderName}</span>
            {showDescriptions && node.description && (
              <div className="text-xs text-gray-500 italic font-normal mt-1">{node.description}</div>
            )}
          </div>

          <div className="bg-transparent">
            {Object.entries(node.properties).map(([childKey, childNode], index) => (
              <div key={childKey}>
                {index > 0 && <div className="border-t border-dashed border-gray-200 -mx-px"></div>}
                <div className="p-3">{renderProperty(childKey, childNode, currentPath)}</div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // For arrays, simple inline display like primitives
    if ((node.type === "array" || node.items) && node.items) {
      const fullKeyPath = annotationPrefix ? `${annotationPrefix}.${currentPath}` : currentPath;
      return (
        <div key={key}>
          <div className="py-1">
            <HoverContainer
              keyPath={fullKeyPath}
              className="inline-block px-2 py-1 rounded"
              annotations={annotations}
              onKeypathSelect={onKeypathSelect ? () => onKeypathSelect(currentPath) : undefined}
            >
              <div className="flex items-center gap-3">
                {renderPropertyName(`${key}:`)}
                {renderTypeBadge("array")}
              </div>
              {showDescriptions && node.description && (
                <div className="text-xs text-gray-500 italic font-normal mt-1">{node.description}</div>
              )}
            </HoverContainer>
          </div>

          <div className="ml-4 mt-2 relative">
            <div className="absolute left-0 top-2 w-3 h-3 border-l border-b border-gray-200"></div>
            <div className="ml-3 mt-2">{renderProperty("", node.items, currentPath)}</div>
          </div>
        </div>
      );
    }

    // For primitive types, simple inline display
    const fullKeyPath = annotationPrefix ? `${annotationPrefix}.${currentPath}` : currentPath;
    return (
      <div key={key} className="py-1">
        <HoverContainer
          keyPath={fullKeyPath}
          className="inline-block px-2 py-1 rounded"
          annotations={annotations}
          onKeypathSelect={onKeypathSelect ? () => onKeypathSelect(currentPath) : undefined}
        >
          <div className="flex items-center gap-3">
            {key && renderPropertyName(`${key}:`)}

            {renderTypeBadge(node.type)}

            {node.enum && <span className="text-xs text-gray-500 font-normal">({node.enum.length} values)</span>}
          </div>

          {showDescriptions && node.description && (
            <div className="text-xs text-gray-500 italic font-normal mt-1">{node.description}</div>
          )}
        </HoverContainer>
      </div>
    );
  };

  const jsonSchema = schema.json_schema as JsonSchemaNode;

  return (
    <div className={`border border-gray-200 rounded-[2px] bg-white ${className}`}>
      <div className="p-3 max-h-80 overflow-y-auto">
        {jsonSchema.type && jsonSchema.type !== "object" && (
          <div className="mb-2">{renderTypeBadge(jsonSchema.type)}</div>
        )}
        {jsonSchema.properties ? (
          <div className="space-y-1">
            {Object.entries(jsonSchema.properties).map(([key, node]) => renderProperty(key, node, ""))}
          </div>
        ) : (
          <div className="text-xs text-gray-500 italic font-normal">no properties defined</div>
        )}
      </div>
    </div>
  );
}
