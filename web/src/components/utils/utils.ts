// Utility functions for experiment components
import {
  Annotation,
  Completion,
  ExperimentCompletion,
  ExperimentWithLookups,
  ExtendedVersion,
  Message,
  OutputSchema,
  Trace,
  Version,
} from "@/types/models";
import { findCommonSubstrings } from "./stringMatchingUtils";

export function getMetricBadgeColor(value: number, values: number[], isHigherBetter: boolean = false) {
  if (!values || values.length === 0) return "bg-transparent border border-gray-200 text-gray-700";

  const sortedValues = [...values].sort((a, b) => a - b);
  const min = sortedValues[0];
  const max = sortedValues[sortedValues.length - 1];

  if (isHigherBetter) {
    if (value === max) return "bg-green-200 border border-green-400 text-green-900";
    if (value === min) return "bg-red-200 border border-red-300 text-red-900";
  } else {
    if (value === min) return "bg-green-200 border border-green-400 text-green-900";
    if (value === max) return "bg-red-200 border border-red-300 text-red-900";
  }

  return "bg-transparent border border-gray-200 text-gray-700";
}

export function getMetricBadgeWithRelative(
  value: number,
  values: number[],
  isHigherBetter: boolean = false,
  metricType?: "cost" | "duration" | "reasoning"
) {
  if (!values || values.length === 0) {
    return {
      color: "bg-transparent border border-gray-200 text-gray-700",
      relativeText: undefined,
      isBest: false,
      isWorst: false,
    };
  }

  const sortedValues = [...values].sort((a, b) => a - b);
  const min = sortedValues[0];
  const max = sortedValues[sortedValues.length - 1];

  // If all values are the same, no relative comparison needed
  if (min === max) {
    return {
      color: "bg-transparent border border-gray-200 text-gray-700",
      relativeText: undefined,
      isBest: false,
      isWorst: false,
    };
  }

  let color: string;
  let isBest = false;
  let isWorst = false;
  let relativeText: string | undefined;

  // Determine comparison text based on metric type and whether this value is better or worse
  const getComparisonText = (isBetterValue: boolean) => {
    if (metricType === "cost") {
      return isBetterValue ? "cheaper" : "more expensive";
    }
    if (metricType === "duration") {
      return isBetterValue ? "faster" : "slower";
    }
    if (metricType === "reasoning") {
      return isBetterValue ? "more efficient" : "less efficient";
    }
    return ""; // Don't show any descriptor for unknown metric types
  };

  if (isHigherBetter) {
    isBest = value === max;
    isWorst = value === min;

    if (isBest) {
      color =
        metricType === "cost" || metricType === "duration" || metricType === "reasoning"
          ? "bg-green-200 border border-green-400 text-green-900"
          : "bg-transparent border border-gray-200 text-gray-700";
      const comparisonText = getComparisonText(true);
      relativeText = comparisonText ? `${(max / min).toFixed(1)}x ${comparisonText}` : `${(max / min).toFixed(1)}x`;
    } else if (isWorst) {
      color =
        metricType === "cost" || metricType === "duration" || metricType === "reasoning"
          ? "bg-red-200 border border-red-300 text-red-900"
          : "bg-transparent border border-gray-200 text-gray-700";
      const comparisonText = getComparisonText(false);
      relativeText = comparisonText ? `${(value / min).toFixed(1)}x ${comparisonText}` : `${(value / min).toFixed(1)}x`;
    } else {
      color = "bg-transparent border border-gray-200 text-gray-700";
    }

    // For non-best values, show how much worse they are
    if (!isBest && max > 0) {
      if (metricType === "cost" || metricType === "duration" || metricType === "reasoning") {
        relativeText = `${(max / value).toFixed(1)}x ${getComparisonText(false)}`;
      } else {
        relativeText = `${(max / value).toFixed(1)}x`;
      }
    }
  } else {
    isBest = value === min;
    isWorst = value === max;

    if (isBest) {
      color =
        metricType === "cost" || metricType === "duration" || metricType === "reasoning"
          ? "bg-green-200 border border-green-400 text-green-900"
          : "bg-transparent border border-gray-200 text-gray-700";
      const comparisonText = getComparisonText(true);
      relativeText = comparisonText ? `${(max / min).toFixed(1)}x ${comparisonText}` : `${(max / min).toFixed(1)}x`;
    } else if (isWorst) {
      color =
        metricType === "cost" || metricType === "duration" || metricType === "reasoning"
          ? "bg-red-200 border border-red-300 text-red-900"
          : "bg-transparent border border-gray-200 text-gray-700";
      const comparisonText = getComparisonText(false);
      relativeText = comparisonText ? `${(value / min).toFixed(1)}x ${comparisonText}` : `${(value / min).toFixed(1)}x`;
    } else {
      color = "bg-transparent border border-gray-200 text-gray-700";
    }

    // For non-best values, show how much worse they are
    if (!isBest && min > 0) {
      if (metricType === "cost" || metricType === "duration" || metricType === "reasoning") {
        relativeText = `${(value / min).toFixed(1)}x ${getComparisonText(false)}`;
      } else {
        relativeText = `${(value / min).toFixed(1)}x`;
      }
    }
  }

  return {
    color,
    relativeText,
    isBest,
    isWorst,
    showArrow: !metricType, // Only show arrows for non-cost/duration metrics
  };
}

export function formatCurrency(value: number, multiplier: number): string {
  // Convert using multiplier for better readability
  const adjustedValue = value * multiplier;
  return `$${adjustedValue.toFixed(2)}`;
}

export function formatTotalCost(value: unknown): string {
  return value ? `$${Math.max(Number(value), 0.01).toFixed(2)}` : "-";
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

export function formatRelativeDateWithTime(value: unknown): string {
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

  // For older dates, show both date and time
  return `${date.toLocaleDateString()}, ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export function formatDate(
  value: unknown,
  format: "date" | "datetime" | "time" | "relative" | "relative_with_time"
): string {
  if (value === null || value === undefined) return "N/A";

  // Only add 'Z' suffix for dates that contain time information and don't already have timezone info
  const dateString = String(value);
  const hasTimeComponent = /T\d{2}:\d{2}|[ ]\d{2}:\d{2}/.test(dateString);
  const hasTimezone = /[Z+\-]\d{2}:?\d{2}?$/.test(dateString);
  const utcDateString = hasTimeComponent && !hasTimezone ? dateString + "Z" : dateString;

  // Try UTC date first, fallback to original if parsing fails
  let date = new Date(utcDateString);
  let finalDateString = utcDateString;

  if (isNaN(date.getTime())) {
    date = new Date(dateString);
    finalDateString = dateString;
    if (isNaN(date.getTime())) return dateString;
  }

  // If there's no time component, always format as date-only regardless of the format parameter
  if (!hasTimeComponent) {
    return date.toLocaleDateString();
  }

  switch (format) {
    case "datetime":
      return date.toLocaleString();
    case "time":
      return date.toLocaleTimeString();
    case "relative":
      return formatRelativeDate(finalDateString);
    case "relative_with_time":
      return formatRelativeDateWithTime(finalDateString);
    default:
      return date.toLocaleDateString();
  }
}

// Utility functions for error-based filtering
export function shouldIncludeCostMetric(
  completion: ExperimentCompletion | undefined
): completion is ExperimentCompletion {
  return completion != null && completion.cost_usd != null && !(completion.cost_usd === 0 && completion.output?.error);
}

export function shouldIncludeDurationMetric(
  completion: ExperimentCompletion | undefined
): completion is ExperimentCompletion {
  return (
    completion != null &&
    completion.duration_seconds != null &&
    !(completion.duration_seconds === 0 && completion.output?.error)
  );
}

export function shouldIncludeReasoningMetric(
  completion: ExperimentCompletion | undefined
): completion is ExperimentCompletion {
  return (
    completion != null &&
    getReasoningTokenCount(completion) !== undefined &&
    !completion.output?.error
  );
}

export function getValidCosts(completions: (ExperimentCompletion | undefined)[]): number[] {
  return completions
    .filter((completion): completion is ExperimentCompletion => shouldIncludeCostMetric(completion))
    .map((completion) => completion.cost_usd);
}

export function getValidDurations(completions: (ExperimentCompletion | undefined)[]): number[] {
  return completions
    .filter((completion): completion is ExperimentCompletion => shouldIncludeDurationMetric(completion))
    .map((completion) => completion.duration_seconds);
}

export function getValidReasoningTokens(completions: (ExperimentCompletion | undefined)[]): number[] {
  return completions
    .filter((completion): completion is ExperimentCompletion => shouldIncludeReasoningMetric(completion))
    .map((completion) => getReasoningTokenCount(completion))
    .filter((tokens): tokens is number => tokens !== undefined);
}

export function calculateAverageMetrics(completions: ExperimentCompletion[]): {
  avgCost: number | undefined;
  avgDuration: number | undefined;
  avgReasoningTokens: number | undefined;
  costs: number[];
  durations: number[];
  reasoningTokens: number[];
} {
  if (completions.length === 0) return { avgCost: undefined, avgDuration: undefined, avgReasoningTokens: undefined, costs: [], durations: [], reasoningTokens: [] };

  // Use centralized filtering logic
  const costs = getValidCosts(completions);
  const durations = getValidDurations(completions);
  const reasoningTokens = getValidReasoningTokens(completions);

  const totalCost = costs.reduce((sum, cost) => sum + cost, 0);
  const totalDuration = durations.reduce((sum, duration) => sum + duration, 0);
  const totalReasoningTokens = reasoningTokens.reduce((sum, tokens) => sum + tokens, 0);

  return {
    avgCost: costs.length > 0 ? totalCost / costs.length : undefined,
    avgDuration: durations.length > 0 ? totalDuration / durations.length : undefined,
    avgReasoningTokens: reasoningTokens.length > 0 ? totalReasoningTokens / reasoningTokens.length : undefined,
    costs,
    durations,
    reasoningTokens,
  };
}

export function getCompletionsPerVersion(experiment: ExperimentWithLookups): Array<{
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
    const completionsForVersion = experiment.completions!.filter((completion) => completion.version.id === version.id);

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
  metrics: { 
    avgCost: number | undefined; 
    avgDuration: number | undefined; 
    avgReasoningTokens: number | undefined;
    costs: number[]; 
    durations: number[];
    reasoningTokens: number[];
  };
}> {
  return completionsPerVersion.map(({ versionId, completions }) => ({
    versionId,
    metrics: calculateAverageMetrics(completions),
  }));
}

export const IGNORED_VERSION_KEYS: string[] = ["id", "alias"];

export function getDifferingVersionKeys(versions: Version[]): string[] {
  if (versions.length <= 1) return Object.keys([]);

  const keysToShow: string[] = [];
  const keysToAlwaysShow: string[] = ["model"];

  // Gather all unique keys from all versions
  const allKeys = new Set<string>();
  versions.forEach((version) => {
    Object.keys(version).forEach((key) => allKeys.add(key));
  });

  const filteredKeys = Array.from(allKeys).filter(
    (key) => !keysToAlwaysShow.includes(key) && !IGNORED_VERSION_KEYS.includes(key)
  );

  for (const key of filteredKeys) {
    const values = versions.map((version) => {
      const value = version[key as keyof Version];

      // Convert all values to strings for consistent comparison
      if (value === null || value === undefined) {
        return "null";
      }

      if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
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
    use_cache: extendedVersion.use_cache !== undefined ? extendedVersion.use_cache : "auto",
    max_tokens: extendedVersion.max_tokens !== undefined ? extendedVersion.max_tokens : "unlimited",
    stream: extendedVersion.stream !== undefined ? extendedVersion.stream : false,
    include_usage: extendedVersion.include_usage !== undefined ? extendedVersion.include_usage : false,
    presence_penalty: extendedVersion.presence_penalty !== undefined ? extendedVersion.presence_penalty : 0,
    frequency_penalty: extendedVersion.frequency_penalty !== undefined ? extendedVersion.frequency_penalty : 0,
    stop: extendedVersion.stop !== undefined ? extendedVersion.stop : "none",
    tool_choice: extendedVersion.tool_choice !== undefined ? extendedVersion.tool_choice : "auto",
  };
}

export function getVersionKeys(versions: Version[]): string[] {
  if (versions.length === 0) return [];

  // Apply defaults to all versions
  const versionsWithDefaults = versions.map(getVersionWithDefaults);

  // Gather all unique keys from all versions (including default keys)
  const allKeys = new Set<string>();
  versionsWithDefaults.forEach((version) => {
    Object.keys(version).forEach((key) => allKeys.add(key));
  });

  // Return all keys except blacklisted ones
  return Array.from(allKeys).filter((key) => !IGNORED_VERSION_KEYS.includes(key));
}

// Helper function to normalize objects and arrays for order-independent comparison
export function normalizeForComparison(value: unknown): string {
  if (value === null || value === undefined) {
    return "null";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    // Sort array elements for consistent ordering
    const sortedArray = [...value].sort((a, b) => {
      const normalizedA = normalizeForComparison(a);
      const normalizedB = normalizeForComparison(b);
      return normalizedA.localeCompare(normalizedB);
    });
    return JSON.stringify(sortedArray);
  }

  if (typeof value === "object") {
    // Sort object keys and recursively normalize values
    const sortedKeys = Object.keys(value as Record<string, unknown>).sort();
    const normalizedObj: Record<string, unknown> = {};

    for (const key of sortedKeys) {
      const objValue = (value as Record<string, unknown>)[key];
      // For primitive values, store them directly
      if (
        objValue === null ||
        objValue === undefined ||
        typeof objValue === "string" ||
        typeof objValue === "number" ||
        typeof objValue === "boolean"
      ) {
        normalizedObj[key] = objValue;
      } else {
        // For complex values, parse the normalized string back to object/array
        try {
          normalizedObj[key] = JSON.parse(normalizeForComparison(objValue));
        } catch {
          // If parsing fails, fall back to string representation
          normalizedObj[key] = String(objValue);
        }
      }
    }

    return JSON.stringify(normalizedObj);
  }

  return String(value);
}

export function getMatchingVersionKeys(versions: Version[], blackListedKeys: string[] = ["id", "alias"]): string[] {
  // For single version, return all keys (including defaults) except blacklisted ones
  if (versions.length === 1) {
    const versionWithDefaults = getVersionWithDefaults(versions[0]);
    const allKeys = Object.keys(versionWithDefaults as unknown as Record<string, unknown>);
    return allKeys.filter((key) => !blackListedKeys.includes(key));
  }

  if (versions.length === 0) return [];

  // Apply defaults to all versions
  const versionsWithDefaults = versions.map(getVersionWithDefaults);

  // Gather all unique keys from all versions (including default keys)
  const allKeys = new Set<string>();
  versionsWithDefaults.forEach((version) => {
    Object.keys(version).forEach((key) => allKeys.add(key));
  });

  const filteredKeys = Array.from(allKeys).filter((key) => !blackListedKeys.includes(key));

  // Check which keys have matching values across all versions
  const matchingKeys: string[] = [];

  for (const key of filteredKeys) {
    const values = versionsWithDefaults.map((version) => {
      const value = (version as unknown as Record<string, unknown>)[key];
      return normalizeForComparison(value);
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
  return completions.find((completion) => completion.input.id === inputId && completion.version.id === versionId);
}

export function findIndexOfVersionThatFirstUsedThosePromptAndSchema(
  versions: Version[],
  currentVersion: Version
): number | undefined {
  // Helper function to check if prompt is empty/undefined
  const isPromptEmpty = (prompt: Message[] | undefined | null) => !prompt || prompt.length === 0;

  // Helper function to check if schema is empty/undefined
  const isSchemaEmpty = (schema: object | undefined | null) => !schema || Object.keys(schema).length === 0;

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
    const schemasMatch = JSON.stringify(v.output_schema) === currentSchemaString;

    return promptsMatch && schemasMatch;
  });

  return foundIndex === -1 ? undefined : foundIndex;
}

export function findIndexOfVersionThatFirstUsedThosePrompt(
  versions: Version[],
  currentVersion: Version
): number | undefined {
  // Helper function to check if prompt is empty/undefined
  const isPromptEmpty = (prompt: Message[] | undefined | null) => !prompt || prompt.length === 0;

  // Check if current version has prompt
  if (isPromptEmpty(currentVersion.prompt)) {
    return undefined;
  }

  const currentPromptString = JSON.stringify(currentVersion.prompt);

  const foundIndex = versions.findIndex((v) => {
    // Skip empty prompts
    if (isPromptEmpty(v.prompt)) {
      return false;
    }

    // Prompt must match
    return JSON.stringify(v.prompt) === currentPromptString;
  });

  return foundIndex === -1 ? undefined : foundIndex;
}

export function findIndexOfVersionThatFirstUsedThoseSchema(
  versions: Version[],
  currentVersion: Version
): number | undefined {
  // Helper function to check if schema is empty/undefined
  const isSchemaEmpty = (schema: object | undefined | null) => !schema || Object.keys(schema).length === 0;

  // Check if current version has schema
  if (isSchemaEmpty(currentVersion.output_schema)) {
    return undefined;
  }

  const currentSchemaString = JSON.stringify(currentVersion.output_schema);

  const foundIndex = versions.findIndex((v) => {
    // Skip empty schemas
    if (isSchemaEmpty(v.output_schema)) {
      return false;
    }

    // Schema must match
    return JSON.stringify(v.output_schema) === currentSchemaString;
  });

  return foundIndex === -1 ? undefined : foundIndex;
}

export function getSharedPartsOfPrompts(versions: Version[]): Message[] {
  if (!versions || versions.length === 0) {
    return [];
  }

  // Filter versions that have prompts
  const versionsWithPrompts = versions.filter((v) => v.prompt && v.prompt.length > 0);

  if (versionsWithPrompts.length === 0) {
    return [];
  }

  // If only one version has prompts, return its prompt
  if (versionsWithPrompts.length === 1) {
    return versionsWithPrompts[0].prompt || [];
  }

  // Get the maximum number of messages across all prompts
  const maxMessages = Math.max(...versionsWithPrompts.map((v) => (v.prompt || []).length));
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
            role: role as "system" | "user" | "assistant" | "developer" | "tool",
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
function extractKeyPaths(obj: Record<string, unknown>, prefix: string = ""): string[] {
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
        paths.push(...extractKeyPaths(valueObj.properties as Record<string, unknown>, currentPath));
      }

      // Handle JSON Schema array items - properties go directly under the array path
      if (valueObj.items && typeof valueObj.items === "object") {
        const itemsObj = valueObj.items as Record<string, unknown>;
        if (itemsObj.properties) {
          paths.push(...extractKeyPaths(itemsObj.properties as Record<string, unknown>, currentPath));
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
    (v) => v.output_schema && typeof v.output_schema === "object" && Object.keys(v.output_schema).length > 0
  );

  if (versionsWithSchemas.length === 0) {
    return [];
  }

  // If only one version has a schema, return all its key paths
  if (versionsWithSchemas.length === 1) {
    const schema = versionsWithSchemas[0].output_schema as unknown as Record<string, unknown>;
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
  const sharedPaths = firstSchemaPaths.filter((path) => allKeyPaths.every((schemaPaths) => schemaPaths.includes(path)));

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

export function isJSONSchema(parsedJSON: unknown): boolean {
  if (!parsedJSON || typeof parsedJSON !== "object") return false;
  const obj = parsedJSON as Record<string, unknown>;

  // Check if it has the structure of an OutputSchema (id + json_schema)
  if (obj.id && obj.json_schema) return true;

  // Check if it looks like a raw JSON schema (has typical schema properties)
  const schemaIndicators = ["type", "$schema", "properties", "required", "definitions", "$defs"];
  return schemaIndicators.some((indicator) => indicator in obj);
}

export function createOutputSchemaFromJSON(parsedJSON: unknown, fallbackId: string): OutputSchema | null {
  if (!parsedJSON || typeof parsedJSON !== "object") return null;

  const obj = parsedJSON as Record<string, unknown>;

  // If it already has the OutputSchema structure
  if (obj.id && obj.json_schema && typeof obj.id === "string" && typeof obj.json_schema === "object") {
    return { id: obj.id as string, json_schema: obj.json_schema as Record<string, unknown> };
  }

  // If it's a raw JSON schema, wrap it in OutputSchema format
  return {
    id: fallbackId || "detected-schema",
    json_schema: obj,
  };
}

export function isDateValue(value: unknown): boolean {
  if (typeof value === "string") {
    // Check for common date formats more strictly
    // ISO date: YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss variants
    // Common date formats: MM/DD/YYYY, DD-MM-YYYY, etc.
    const isoDateRegex = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d{3})?(Z|[+-]\d{2}:\d{2})?)?$/;
    const commonDateRegex = /^(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})$/;

    // Only check if it's a valid date if it matches expected date patterns
    if (isoDateRegex.test(value) || commonDateRegex.test(value)) {
      const date = new Date(value);
      return !isNaN(date.getTime());
    }
  }
  return false;
}

export function transformCompletionsData(data: Record<string, unknown>[]): Record<string, unknown>[] {
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

export function filterAnnotations(annotations: Annotation[] | undefined, filters: AnnotationFilters): Annotation[] {
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
        annotation.target?.experiment_id === experimentId || annotation.context?.experiment_id === experimentId;
      if (!hasExperimentId) {
        return false;
      }
    }

    // Filter by exact key path
    if (keyPath && annotation.target?.key_path !== keyPath) {
      return false;
    }

    // Filter by key path prefix
    if (keyPathPrefix && !annotation.target?.key_path?.startsWith(keyPathPrefix)) {
      return false;
    }

    return true;
  });
}

// JSON Schema utilities
export type JsonSchemaNode = {
  type?: string | string[];
  properties?: Record<string, JsonSchemaNode>;
  items?: JsonSchemaNode;
  required?: string[];
  description?: string;
  enum?: unknown[];
  default?: unknown;
  examples?: unknown[];
  $ref?: string;
  $defs?: Record<string, JsonSchemaNode>;
};

/**
 * Resolves JSON Schema $ref references
 * @param node - The schema node that may contain a $ref
 * @param rootSchema - The root schema containing definitions
 * @returns The resolved schema node
 */
export function resolveRef(node: JsonSchemaNode, rootSchema: JsonSchemaNode): JsonSchemaNode {
  if (!node.$ref) return node;

  // Handle internal references like "#/$defs/DayMeals"
  if (node.$ref.startsWith("#/")) {
    const path = node.$ref.substring(2); // Remove "#/"
    const pathParts = path.split("/");

    let current: unknown = rootSchema;
    for (const part of pathParts) {
      if (current && typeof current === "object" && current !== null && part in current) {
        current = (current as Record<string, unknown>)[part];
      } else {
        console.warn(`Could not resolve $ref: ${node.$ref}`);
        return node; // Return original node if resolution fails
      }
    }

    return current as JsonSchemaNode;
  }

  // Handle other types of references if needed in the future
  console.warn(`Unsupported $ref format: ${node.$ref}`);
  return node;
}

/**
 * Simple function to strip markdown formatting
 */
export function stripMarkdown(markdown: string): string {
  return markdown
    .replace(/#{1,6}\s/g, "") // Remove headers
    .replace(/\*\*(.*?)\*\*/g, "$1") // Remove bold
    .replace(/\*(.*?)\*/g, "$1") // Remove italic
    .replace(/`(.*?)`/g, "$1") // Remove inline code
    .replace(/\[(.*?)\]\(.*?\)/g, "$1") // Remove links, keep text
    .replace(/>\s/g, "") // Remove blockquotes
    .replace(/^\s*[-*+]\s/gm, "") // Remove list markers
    .replace(/^\s*\d+\.\s/gm, "") // Remove numbered list markers
    .replace(/\n+/g, " ") // Replace newlines with spaces
    .trim();
}

/**
 * Extracts the reasoning token count from a completion's traces.
 * Looks through all LLM traces and returns the total reasoning tokens used.
 * 
 * @param completion - The completion object containing traces
 * @returns The total number of reasoning tokens used, or undefined if reasoning tokens are not present in the trace structure
 */
export function getReasoningTokenCount(completion: Completion | ExperimentCompletion): number | undefined {
  // For ExperimentCompletion, use the direct reasoning_token_count field
  if ('reasoning_token_count' in completion) {
    return completion.reasoning_token_count;
  }
  
  // For regular Completion, fall back to parsing traces
  const traces = 'traces' in completion ? completion.traces : undefined;
  
  if (!traces || !Array.isArray(traces)) {
    return undefined;
  }

  let totalReasoningTokens = 0;
  let hasReasoningField = false;

  for (const trace of traces) {
    // Only check LLM traces
    if (trace.kind !== "llm") continue;

    const llmTrace = trace as Extract<Trace, { kind: "llm" }>;
    
    // Check if trace has usage data
    if (!llmTrace.usage) continue;

    // Handle both new detailed usage structure and old simple structure
    if ("completion" in llmTrace.usage && llmTrace.usage.completion) {
      const completionUsage = llmTrace.usage.completion;
      
      // Check if reasoning_token_count field exists (even if it's 0)
      if ('reasoning_token_count' in completionUsage && completionUsage.reasoning_token_count !== undefined) {
        hasReasoningField = true;
        totalReasoningTokens += completionUsage.reasoning_token_count || 0;
      }
    }
  }

  // Return undefined if no traces had reasoning_token_count field
  // Return the total (including 0) if the field was present
  return hasReasoningField ? totalReasoningTokens : undefined;
}

/**
 * Checks if a completion used reasoning (has reasoning tokens > 0)
 * 
 * @param completion - The completion object to check
 * @returns True if the completion used reasoning, false if no reasoning or reasoning tokens not present
 */
export function hasReasoningTokens(completion: Completion | ExperimentCompletion): boolean {
  const reasoningTokens = getReasoningTokenCount(completion);
  return reasoningTokens !== undefined && reasoningTokens > 0;
}

/**
 * Gets a summary of token usage from completion traces including reasoning tokens
 * 
 * @param completion - The completion object containing traces
 * @returns Object with token usage breakdown, reasoningTokens is undefined if not present in trace
 */
export function getTokenUsageSummary(completion: Completion | ExperimentCompletion): {
  promptTokens: number;
  completionTokens: number;
  reasoningTokens: number | undefined;
  cachedTokens: number;
  totalTokens: number;
} {
  const traces = 'traces' in completion ? completion.traces : undefined;
  
  let promptTokens = 0;
  let completionTokens = 0;
  let reasoningTokens: number | undefined = undefined;
  let cachedTokens = 0;
  let hasReasoningField = false;

  if (traces && Array.isArray(traces)) {
    for (const trace of traces) {
      if (trace.kind !== "llm") continue;

      const llmTrace = trace as Extract<Trace, { kind: "llm" }>;
      
      if (!llmTrace.usage) continue;

      // Handle detailed usage structure
      if ("prompt" in llmTrace.usage && "completion" in llmTrace.usage) {
        const usage = llmTrace.usage as {
          prompt: { text_token_count?: number };
          completion: { text_token_count?: number; reasoning_token_count?: number; cached_token_count?: number };
        };

        if (usage.prompt.text_token_count) {
          promptTokens += usage.prompt.text_token_count;
        }

        if (usage.completion.text_token_count) {
          completionTokens += usage.completion.text_token_count;
        }

        if ('reasoning_token_count' in usage.completion && usage.completion.reasoning_token_count !== undefined) {
          if (!hasReasoningField) {
            hasReasoningField = true;
            reasoningTokens = 0; // Initialize when we first find the field
          }
          reasoningTokens = (reasoningTokens || 0) + (usage.completion.reasoning_token_count || 0);
        }

        if (usage.completion.cached_token_count) {
          cachedTokens += usage.completion.cached_token_count;
        }
      }
    }
  }

  return {
    promptTokens,
    completionTokens,
    reasoningTokens,
    cachedTokens,
    totalTokens: promptTokens + completionTokens + (reasoningTokens || 0),
  };
}
