// Utility functions for experiment components
import {
  Annotation,
  ExperimentCompletion,
  ExperimentWithLookups,
  ExtendedVersion,
  Message,
  Version,
} from "@/types/models";
import { findCommonSubstrings } from "./stringMatchingUtils";

export function getMetricBadgeColor(
  value: number,
  values: number[],
  isHigherBetter: boolean = false
) {
  if (!values || values.length === 0)
    return "bg-transparent border border-gray-200 text-gray-700";

  const sortedValues = [...values].sort((a, b) => a - b);
  const min = sortedValues[0];
  const max = sortedValues[sortedValues.length - 1];

  if (isHigherBetter) {
    if (value === max)
      return "bg-green-200 border border-green-400 text-green-900";
    if (value === min) return "bg-red-200 border border-red-300 text-red-900";
  } else {
    if (value === min)
      return "bg-green-200 border border-green-400 text-green-900";
    if (value === max) return "bg-red-200 border border-red-300 text-red-900";
  }

  return "bg-transparent border border-gray-200 text-gray-700";
}

export function formatCurrency(
  value: number,
  multiplier: number = 1000
): string {
  // Convert using multiplier for better readability
  const adjustedValue = value * multiplier;
  return `$${adjustedValue.toFixed(2)}`;
}

export function formatDuration(seconds: number): string {
  return `${seconds.toFixed(2)}s`;
}

export function formatRelativeDate(value: unknown): string {
  if (value === null || value === undefined) return "N/A";

  const date = new Date(String(value));
  if (isNaN(date.getTime())) return "Invalid Date";

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
}

export function calculateAverageMetrics(completions: ExperimentCompletion[]): {
  avgCost: number;
  avgDuration: number;
} {
  if (completions.length === 0) return { avgCost: 0, avgDuration: 0 };

  const totalCost = completions.reduce(
    (sum, completion) => sum + (completion.cost_usd || 0),
    0
  );
  const totalDuration = completions.reduce(
    (sum, completion) => sum + (completion.duration_seconds || 0),
    0
  );

  return {
    avgCost: totalCost / completions.length,
    avgDuration: totalDuration / completions.length,
  };
}

export function getCompletionsPerVersion(
  experiment: ExperimentWithLookups
): Array<{
  versionId: string;
  completions: ExperimentCompletion[];
}> {
  if (!experiment.completions || !experiment.versions) {
    return [];
  }

  const groupedArray: Array<{
    versionId: string;
    completions: ExperimentCompletion[];
  }> = [];

  experiment.versions.forEach((version) => {
    const completionsForVersion = experiment.completions!.filter(
      (completion) => completion.version.id === version.id
    );

    if (completionsForVersion.length > 0) {
      groupedArray.push({
        versionId: version.id,
        completions: completionsForVersion,
      });
    }
  });

  return groupedArray;
}

export function getPriceAndLatencyPerVersion(
  completionsPerVersion: Array<{
    versionId: string;
    completions: ExperimentCompletion[];
  }>
): Array<{
  versionId: string;
  metrics: { avgCost: number; avgDuration: number };
}> {
  return completionsPerVersion.map(({ versionId, completions }) => ({
    versionId,
    metrics: calculateAverageMetrics(completions),
  }));
}

export function getDifferingVersionKeys(versions: Version[]): string[] {
  if (versions.length <= 1) return Object.keys([]);

  const keysToShow: string[] = [];
  const keysToAlwaysShow: string[] = ["model"];
  const blackListedKeys: string[] = ["id"];

  // Gather all unique keys from all versions
  const allKeys = new Set<string>();
  versions.forEach((version) => {
    Object.keys(version).forEach((key) => allKeys.add(key));
  });

  const filteredKeys = Array.from(allKeys).filter(
    (key) => !keysToAlwaysShow.includes(key) && !blackListedKeys.includes(key)
  );

  for (const key of filteredKeys) {
    const values = versions.map((version) => {
      const value = version[key as keyof Version];

      // Convert all values to strings for consistent comparison
      if (value === null || value === undefined) {
        return "null";
      }

      if (
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      ) {
        return String(value);
      }

      if (Array.isArray(value)) {
        return JSON.stringify(value);
      }

      if (typeof value === "object") {
        return JSON.stringify(value);
      }

      return String(value);
    });

    // Check if all values are the same
    const uniqueValues = new Set(values);
    if (uniqueValues.size > 1) {
      keysToShow.push(key);
    }
  }

  return keysToShow;
}

export function getVersionKeyDisplayName(key: string): string {
  const displayNames: Record<string, string> = {
    prompt: "Prompt",
    output_schema: "Output Schema",
    temperature: "Temperature",
    use_cache: "Use Cache",
    max_tokens: "Max Tokens",
    top_p: "Top P",
    stream: "Stream",
    include_usage: "Include Usage",
    presence_penalty: "Presence Penalty",
    frequency_penalty: "Frequency Penalty",
    stop: "Stop",
    tool_choice: "Tool Choice",
    tools: "Available Tools",
    model: "Model",
  };

  return displayNames[key] || key;
}

export function sortVersionKeys(keys: string[]): string[] {
  const keyOrder = [
    "prompt",
    "output_schema",
    "temperature",
    "use_cache",
    "max_tokens",
    "top_p",
    "stream",
    "include_usage",
    "presence_penalty",
    "frequency_penalty",
    "stop",
    "tool_choice",
    "tools",
  ];

  // Sort keys based on the defined order, with unknown keys at the end
  return keys.sort((a, b) => {
    const indexA = keyOrder.indexOf(a);
    const indexB = keyOrder.indexOf(b);

    // If both keys are in the order list, sort by their position
    if (indexA !== -1 && indexB !== -1) {
      return indexA - indexB;
    }

    // If only one key is in the order list, prioritize it
    if (indexA !== -1) return -1;
    if (indexB !== -1) return 1;

    // If neither key is in the order list, sort alphabetically
    return a.localeCompare(b);
  });
}

export function getVersionWithDefaults(version: Version): ExtendedVersion {
  const extendedVersion = version as ExtendedVersion;
  return {
    ...version,
    temperature: version.temperature !== undefined ? version.temperature : 1.0,
    top_p: version.top_p !== undefined ? version.top_p : 1.0,
    tools: version.tools !== undefined ? version.tools : [],
    use_cache:
      extendedVersion.use_cache !== undefined
        ? extendedVersion.use_cache
        : "auto",
    max_tokens:
      extendedVersion.max_tokens !== undefined
        ? extendedVersion.max_tokens
        : "unlimited",
    stream:
      extendedVersion.stream !== undefined ? extendedVersion.stream : false,
    include_usage:
      extendedVersion.include_usage !== undefined
        ? extendedVersion.include_usage
        : false,
    presence_penalty:
      extendedVersion.presence_penalty !== undefined
        ? extendedVersion.presence_penalty
        : 0,
    frequency_penalty:
      extendedVersion.frequency_penalty !== undefined
        ? extendedVersion.frequency_penalty
        : 0,
    stop: extendedVersion.stop !== undefined ? extendedVersion.stop : "none",
    tool_choice:
      extendedVersion.tool_choice !== undefined
        ? extendedVersion.tool_choice
        : "auto",
  };
}

export function getVersionKeys(versions: Version[]): string[] {
  if (versions.length === 0) return [];

  const blackListedKeys: string[] = ["id"];

  // Apply defaults to all versions
  const versionsWithDefaults = versions.map(getVersionWithDefaults);

  // Gather all unique keys from all versions (including default keys)
  const allKeys = new Set<string>();
  versionsWithDefaults.forEach((version) => {
    Object.keys(version).forEach((key) => allKeys.add(key));
  });

  // Return all keys except blacklisted ones
  return Array.from(allKeys).filter((key) => !blackListedKeys.includes(key));
}

export function getMatchingVersionKeys(versions: Version[]): string[] {
  // For single version, return all keys (including defaults) except blacklisted ones
  if (versions.length === 1) {
    const blackListedKeys: string[] = ["id"];
    const versionWithDefaults = getVersionWithDefaults(versions[0]);
    const allKeys = Object.keys(
      versionWithDefaults as unknown as Record<string, unknown>
    );
    return allKeys.filter((key) => !blackListedKeys.includes(key));
  }

  if (versions.length === 0) return [];

  const blackListedKeys: string[] = ["id", "model"];

  // Apply defaults to all versions
  const versionsWithDefaults = versions.map(getVersionWithDefaults);

  // Gather all unique keys from all versions (including default keys)
  const allKeys = new Set<string>();
  versionsWithDefaults.forEach((version) => {
    Object.keys(version).forEach((key) => allKeys.add(key));
  });

  const filteredKeys = Array.from(allKeys).filter(
    (key) => !blackListedKeys.includes(key)
  );

  // Check which keys have matching values across all versions
  const matchingKeys: string[] = [];

  for (const key of filteredKeys) {
    const values = versionsWithDefaults.map((version) => {
      const value = (version as unknown as Record<string, unknown>)[key];

      // Convert all values to strings for consistent comparison
      if (value === null || value === undefined) {
        return "null";
      }

      if (
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      ) {
        return String(value);
      }

      if (Array.isArray(value)) {
        return JSON.stringify(value);
      }

      if (typeof value === "object") {
        return JSON.stringify(value);
      }

      return String(value);
    });

    // Check if all values are the same
    const uniqueValues = new Set(values);
    if (uniqueValues.size === 1) {
      matchingKeys.push(key);
    }
  }

  return matchingKeys;
}

export function findCompletionForInputAndVersion(
  completions: ExperimentCompletion[],
  inputId: string,
  versionId: string
): ExperimentCompletion | undefined {
  return completions.find(
    (completion) =>
      completion.input.id === inputId && completion.version.id === versionId
  );
}

export function findIndexOfVersionThatFirstUsedThosePromptAndSchema(
  versions: Version[],
  currentVersion: Version
): number | undefined {
  // Helper function to check if prompt is empty/undefined
  const isPromptEmpty = (prompt: Message[] | undefined | null) =>
    !prompt || prompt.length === 0;

  // Helper function to check if schema is empty/undefined
  const isSchemaEmpty = (schema: object | undefined | null) =>
    !schema || Object.keys(schema).length === 0;

  // Check if current version has both prompt and output schema (or both are empty)
  const currentPromptEmpty = isPromptEmpty(currentVersion.prompt);
  const currentSchemaEmpty = isSchemaEmpty(currentVersion.output_schema);

  // Must have at least one non-empty (prompt or schema)
  if (currentPromptEmpty && currentSchemaEmpty) {
    return undefined;
  }

  const currentPromptString = JSON.stringify(currentVersion.prompt);
  const currentSchemaString = JSON.stringify(currentVersion.output_schema);

  const foundIndex = versions.findIndex((v) => {
    const versionPromptEmpty = isPromptEmpty(v.prompt);
    const versionSchemaEmpty = isSchemaEmpty(v.output_schema);

    // Must have at least one non-empty (prompt or schema)
    if (versionPromptEmpty && versionSchemaEmpty) {
      return false;
    }

    // Both prompt and schema must match (including empty matching empty)
    const promptsMatch = JSON.stringify(v.prompt) === currentPromptString;
    const schemasMatch =
      JSON.stringify(v.output_schema) === currentSchemaString;

    return promptsMatch && schemasMatch;
  });

  return foundIndex === -1 ? undefined : foundIndex;
}

export function getSharedPartsOfPrompts(versions: Version[]): Message[] {
  if (!versions || versions.length === 0) {
    return [];
  }

  // Filter versions that have prompts
  const versionsWithPrompts = versions.filter(
    (v) => v.prompt && v.prompt.length > 0
  );

  if (versionsWithPrompts.length === 0) {
    return [];
  }

  // If only one version has prompts, return its prompt
  if (versionsWithPrompts.length === 1) {
    return versionsWithPrompts[0].prompt || [];
  }

  // Get the maximum number of messages across all prompts
  const maxMessages = Math.max(
    ...versionsWithPrompts.map((v) => (v.prompt || []).length)
  );
  const sharedMessages: Message[] = [];

  // For each message position
  for (let i = 0; i < maxMessages; i++) {
    // Get all messages at this position across versions
    const messagesAtPosition = versionsWithPrompts
      .map((version) => {
        const prompt = version.prompt || [];
        return prompt[i];
      })
      .filter((msg) => msg); // Remove undefined messages

    if (messagesAtPosition.length === 0) continue;

    // Group messages by role
    const messagesByRole: { [role: string]: Message[] } = {};
    messagesAtPosition.forEach((msg) => {
      if (!messagesByRole[msg.role]) {
        messagesByRole[msg.role] = [];
      }
      messagesByRole[msg.role].push(msg);
    });

    // For each role, find shared content
    Object.entries(messagesByRole).forEach(([role, messages]) => {
      if (messages.length < versionsWithPrompts.length) return; // Not all versions have this role at this position

      // Extract text content from messages
      const textContents = messages
        .map((msg) => {
          if (typeof msg.content === "string") {
            return msg.content;
          } else if (Array.isArray(msg.content)) {
            // Handle array of content objects, extract text parts
            return msg.content
              .filter((item) => item.text)
              .map((item) => item.text)
              .join(" ");
          }
          return "";
        })
        .filter((text) => text.trim().length > 0);

      if (textContents.length === versionsWithPrompts.length) {
        // Find common substrings in the text contents
        const sharedContent = findCommonSubstrings(textContents);

        if (sharedContent.trim().length > 0) {
          // Create a message with the shared content
          sharedMessages.push({
            role: role as
              | "system"
              | "user"
              | "assistant"
              | "developer"
              | "tool",
            content: sharedContent,
          });
        }
      }
    });
  }

  return sharedMessages;
}

export function getRoleDisplay(role: string): string {
  switch (role) {
    case "system":
      return "System";
    case "user":
      return "User";
    case "assistant":
      return "Assistant";
    case "developer":
      return "Developer";
    case "tool":
      return "Tool";
    default:
      return role;
  }
}

// Helper function to extract all key paths from a schema object
function extractKeyPaths(
  obj: Record<string, unknown>,
  prefix: string = ""
): string[] {
  if (!obj || typeof obj !== "object") {
    return [];
  }

  const paths: string[] = [];

  Object.keys(obj).forEach((key) => {
    const currentPath = prefix ? `${prefix}.${key}` : key;
    paths.push(currentPath);

    const value = obj[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const valueObj = value as Record<string, unknown>;

      // Handle JSON Schema properties
      if (valueObj.properties) {
        paths.push(
          ...extractKeyPaths(
            valueObj.properties as Record<string, unknown>,
            currentPath
          )
        );
      }

      // Handle JSON Schema array items - properties go directly under the array path
      if (valueObj.items && typeof valueObj.items === "object") {
        const itemsObj = valueObj.items as Record<string, unknown>;
        if (itemsObj.properties) {
          paths.push(
            ...extractKeyPaths(
              itemsObj.properties as Record<string, unknown>,
              currentPath
            )
          );
        }
      }

      // Handle other nested objects
      if (!valueObj.properties && !valueObj.items) {
        paths.push(...extractKeyPaths(valueObj, currentPath));
      }
    }
  });

  return paths;
}

export function getSharedKeypathsOfSchemas(versions: Version[]): string[] {
  if (!versions || versions.length === 0) {
    return [];
  }

  // Filter versions that have output schemas
  const versionsWithSchemas = versions.filter(
    (v) =>
      v.output_schema &&
      typeof v.output_schema === "object" &&
      Object.keys(v.output_schema).length > 0
  );

  if (versionsWithSchemas.length === 0) {
    return [];
  }

  // If only one version has a schema, return all its key paths
  if (versionsWithSchemas.length === 1) {
    const schema = versionsWithSchemas[0].output_schema as unknown as Record<
      string,
      unknown
    >;
    const jsonSchema = schema?.json_schema as Record<string, unknown>;
    const properties = jsonSchema?.properties as Record<string, unknown>;
    if (!properties) return [];

    return extractKeyPaths(properties, "");
  }

  // Extract key paths from all schemas
  const allKeyPaths = versionsWithSchemas.map((version) => {
    const schema = version.output_schema as unknown as Record<string, unknown>;
    const jsonSchema = schema?.json_schema as Record<string, unknown>;
    const properties = jsonSchema?.properties as Record<string, unknown>;
    if (!properties) return [];
    return extractKeyPaths(properties, "");
  });

  // Find paths that exist in all schemas
  const firstSchemaPaths = allKeyPaths[0];
  const sharedPaths = firstSchemaPaths.filter((path) =>
    allKeyPaths.every((schemaPaths) => schemaPaths.includes(path))
  );

  return sharedPaths.sort();
}

export function parseJSONValue(value: unknown): unknown | null {
  if (value && typeof value === "object") {
    return value;
  }

  if (typeof value === "string") {
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  }

  return null;
}

export function isDateValue(value: unknown): boolean {
  if (typeof value === "string") {
    // Check for ISO date format or other common date formats
    const date = new Date(value);
    return (
      !isNaN(date.getTime()) &&
      (value.includes("T") || value.includes("-") || value.includes("/")) &&
      value.length >= 8
    ); // Minimum reasonable date string length
  }
  return false;
}

export function transformCompletionsData(
  data: Record<string, unknown>[]
): Record<string, unknown>[] {
  return data.map((row) => {
    const newRow: Record<string, unknown> = {};

    // Helper function to parse JSON if it's a string, otherwise return as-is
    const tryParseJSON = (value: unknown): unknown => {
      if (typeof value === "string") {
        const parsed = parseJSONValue(value);
        return parsed !== null ? parsed : value;
      }
      return value;
    };

    // Iterate through keys to preserve order
    for (const [key, value] of Object.entries(row)) {
      if (key === "input_messages") {
        // Start building input object if we encounter input_messages
        if (!newRow.input) {
          const mergedInput: Record<string, unknown> = {};
          if (row.input_messages) {
            mergedInput.messages = tryParseJSON(row.input_messages);
          }
          if (row.input_variables) {
            mergedInput.variables = tryParseJSON(row.input_variables);
          }
          newRow.input = JSON.stringify(mergedInput);
        }
      } else if (key === "input_variables") {
        // Skip if input already created, or create it now
        if (!newRow.input) {
          const mergedInput: Record<string, unknown> = {};
          if (row.input_messages) {
            mergedInput.messages = tryParseJSON(row.input_messages);
          }
          if (row.input_variables) {
            mergedInput.variables = tryParseJSON(row.input_variables);
          }
          newRow.input = JSON.stringify(mergedInput);
        }
      } else if (key === "output_messages") {
        // Start building output object if we encounter output_messages
        if (!newRow.output) {
          const mergedOutput: Record<string, unknown> = {};
          if (row.output_messages) {
            mergedOutput.messages = tryParseJSON(row.output_messages);
          }
          if (row.output_error) {
            mergedOutput.error = tryParseJSON(row.output_error);
          }
          newRow.output = JSON.stringify(mergedOutput);
        }
      } else if (key === "output_error") {
        // Skip if output already created, or create it now
        if (!newRow.output) {
          const mergedOutput: Record<string, unknown> = {};
          if (row.output_messages) {
            mergedOutput.messages = tryParseJSON(row.output_messages);
          }
          if (row.output_error) {
            mergedOutput.error = tryParseJSON(row.output_error);
          }
          newRow.output = JSON.stringify(mergedOutput);
        }
      } else {
        // Copy all other keys as-is
        newRow[key] = value;
      }
    }

    return newRow;
  });
}

// Chart data transformation utilities
export function transformToMultiSeriesChartData(
  data: Record<string, unknown>[],
  xField: string,
  yField: string,
  seriesField: string
): Record<string, unknown>[] {
  if (!data || data.length === 0) {
    return [];
  }

  const grouped = new Map<string, Record<string, unknown>>();

  // Get all unique series values first to ensure consistent structure
  const allSeries = new Set<string>();
  data.forEach((row) => {
    const seriesValue = String(row[seriesField] ?? "");
    if (seriesValue) {
      allSeries.add(seriesValue);
    }
  });

  data.forEach((row) => {
    const xValue = String(row[xField] ?? "");
    const yValue = Number(row[yField] ?? 0);
    const seriesValue = String(row[seriesField] ?? "");

    if (!xValue || !seriesValue) {
      return;
    }

    if (!grouped.has(xValue)) {
      // Initialize with all series set to 0
      const newRow: Record<string, unknown> = { x: xValue };
      allSeries.forEach((series) => {
        newRow[series] = 0;
      });
      grouped.set(xValue, newRow);
    }

    const groupedRow = grouped.get(xValue)!;
    groupedRow[seriesValue] = yValue;
  });

  return Array.from(grouped.values());
}

// Annotation filtering utility
export interface AnnotationFilters {
  completionId?: string;
  experimentId?: string;
  keyPath?: string;
  keyPathPrefix?: string;
}

export function filterAnnotations(
  annotations: Annotation[] | undefined,
  filters: AnnotationFilters
): Annotation[] {
  if (!annotations) return [];

  const { completionId, experimentId, keyPath, keyPathPrefix } = filters;

  return annotations.filter((annotation) => {
    // Filter by completion ID
    if (completionId && annotation.target?.completion_id !== completionId) {
      return false;
    }

    // Filter by experiment ID (either in target or context)
    if (experimentId) {
      const hasExperimentId =
        annotation.target?.experiment_id === experimentId ||
        annotation.context?.experiment_id === experimentId;
      if (!hasExperimentId) {
        return false;
      }
    }

    // Filter by exact key path
    if (keyPath && annotation.target?.key_path !== keyPath) {
      return false;
    }

    // Filter by key path prefix
    if (
      keyPathPrefix &&
      !annotation.target?.key_path?.startsWith(keyPathPrefix)
    ) {
      return false;
    }

    return true;
  });
}
