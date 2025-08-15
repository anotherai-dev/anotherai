import { Message } from "@/types/models";
import { CompletionBaseTableCell } from "./CompletionBaseTableCell";
import { CompletionTableInputOutputCell } from "./CompletionTableInputOutputCell";

interface Props {
  value: unknown;
  maxWidth?: string;
  sharedPartsOfPrompts?: Message[];
}

// Type guard to check if value is Message[]
function isMessageArray(value: unknown): value is Message[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    typeof value[0] === "object" &&
    value[0] !== null &&
    "role" in value[0] &&
    "content" in value[0]
  );
}

// Type guard to check if value is Record<string, unknown> (variables)
function isVariablesObject(value: unknown): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    // Make sure it's not already wrapped (doesn't have messages or variables properties)
    !("messages" in value) &&
    !("variables" in value) &&
    !("error" in value)
  );
}

// Type guard to check if value is a container type from transformCompletionsData
function isContainerType(value: unknown): value is Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  const obj = value as Record<string, unknown>;

  // Check if it's an input container (has messages and/or variables)
  const hasMessages = "messages" in obj && Array.isArray(obj.messages);
  const hasVariables = "variables" in obj && typeof obj.variables === "object" && obj.variables !== null;
  const hasError = "error" in obj;

  // It's a container if it has any combination of these properties
  return hasMessages || hasVariables || hasError;
}

export function CompletionObjectTableCell(props: Props) {
  const { value, maxWidth, sharedPartsOfPrompts } = props;

  // Check if it's a container type from transformCompletionsData first
  if (isContainerType(value)) {
    return (
      <CompletionTableInputOutputCell
        value={value}
        maxWidth={maxWidth}
        sharedPartsOfPrompts={sharedPartsOfPrompts}
      />
    );
  }

  // Check if it's a Message array
  if (isMessageArray(value)) {
    // Package messages in the format expected by InputOutputCell
    const wrappedValue = { internal_anotherai_messages: value };
    return (
      <CompletionTableInputOutputCell
        value={wrappedValue}
        maxWidth={maxWidth}
        sharedPartsOfPrompts={sharedPartsOfPrompts}
      />
    );
  }

  // Check if it's a variables object
  if (isVariablesObject(value)) {
    // Package variables in the format expected by InputOutputCell
    const wrappedValue = { internal_anotherai_variables: value };
    return (
      <CompletionTableInputOutputCell
        value={wrappedValue}
        maxWidth={maxWidth}
        sharedPartsOfPrompts={sharedPartsOfPrompts}
      />
    );
  }

  // For other object types, fall back to BaseTableCell
  return <CompletionBaseTableCell value={value} />;
}
