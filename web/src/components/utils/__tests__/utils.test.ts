import { Version } from "@/types/models";
import {
  calculateAverageMetrics,
  filterAnnotations,
  formatCurrency,
  formatDuration,
  formatRelativeDate,
  formatTotalCost,
  getDifferingVersionKeys,
  getMetricBadgeColor,
  getMetricBadgeWithRelative,
  getSharedPartsOfPrompts,
  getValidCosts,
  getValidDurations,
  getVersionKeyDisplayName,
  getVersionWithDefaults,
  isDateValue,
  parseJSONValue,
  resolveRef,
  shouldIncludeCostMetric,
  shouldIncludeDurationMetric,
  sortVersionKeys,
  stripMarkdown,
  transformCompletionsData,
  transformToMultiSeriesChartData,
} from "../utils";

// Mock types for testing
const mockExperimentCompletion = (cost: number, duration: number) => ({
  id: "1",
  cost_usd: cost,
  duration_seconds: duration,
  input: { id: "input-1" },
  version: { id: "version-1" },
  output: { messages: [] },
});

const mockVersion = (overrides: Record<string, unknown> = {}) => ({
  id: "1",
  model: "gpt-4",
  temperature: 0.0,
  top_p: 1.0,
  ...overrides,
});

const mockAnnotation = (overrides: Record<string, unknown> = {}) => ({
  id: "1",
  created_at: "2023-01-01T00:00:00Z",
  author_name: "test-user",
  target: {},
  context: {},
  ...overrides,
});

describe("Metric Badge Functions", () => {
  describe("getMetricBadgeColor", () => {
    it("returns default color for empty values array", () => {
      const result = getMetricBadgeColor(5, []);
      expect(result).toBe("bg-transparent border border-gray-200 text-gray-700");
    });

    it("returns green for best value when lower is better", () => {
      const result = getMetricBadgeColor(1, [1, 2, 3]);
      expect(result).toBe("bg-green-200 border border-green-400 text-green-900");
    });

    it("returns red for worst value when lower is better", () => {
      const result = getMetricBadgeColor(3, [1, 2, 3]);
      expect(result).toBe("bg-red-200 border border-red-300 text-red-900");
    });

    it("returns green for best value when higher is better", () => {
      const result = getMetricBadgeColor(3, [1, 2, 3], true);
      expect(result).toBe("bg-green-200 border border-green-400 text-green-900");
    });

    it("returns default color for middle values", () => {
      const result = getMetricBadgeColor(2, [1, 2, 3]);
      expect(result).toBe("bg-transparent border border-gray-200 text-gray-700");
    });
  });

  describe("getMetricBadgeWithRelative", () => {
    it("handles empty values array", () => {
      const result = getMetricBadgeWithRelative(5, []);
      expect(result).toEqual({
        color: "bg-transparent border border-gray-200 text-gray-700",
        relativeText: undefined,
        isBest: false,
        isWorst: false,
      });
    });

    it("handles all equal values", () => {
      const result = getMetricBadgeWithRelative(5, [5, 5, 5]);
      expect(result).toEqual({
        color: "bg-transparent border border-gray-200 text-gray-700",
        relativeText: undefined,
        isBest: false,
        isWorst: false,
      });
    });

    it("calculates relative text for best value when lower is better", () => {
      const result = getMetricBadgeWithRelative(1, [1, 2, 4]);
      expect(result.isBest).toBe(true);
      expect(result.relativeText).toBe("4.0x");
    });

    it("calculates relative text for non-best values when lower is better", () => {
      const result = getMetricBadgeWithRelative(2, [1, 2, 4]);
      expect(result.isBest).toBe(false);
      expect(result.relativeText).toBe("2.0x");
    });

    it("calculates relative text for best value when higher is better", () => {
      const result = getMetricBadgeWithRelative(4, [1, 2, 4], true);
      expect(result.isBest).toBe(true);
      expect(result.relativeText).toBe("4.0x");
    });
  });
});

describe("Formatting Functions", () => {
  describe("formatCurrency", () => {
    it("formats currency with 1000 multiplier", () => {
      expect(formatCurrency(0.001, 1000)).toBe("$1.00");
    });

    it("formats currency with custom multiplier", () => {
      expect(formatCurrency(0.001, 100)).toBe("$0.10");
    });

    it("handles zero value", () => {
      expect(formatCurrency(0, 1000)).toBe("$0.00");
    });
  });

  describe("formatTotalCost", () => {
    it("formats valid numbers", () => {
      expect(formatTotalCost(1.234)).toBe("$1.23");
    });

    it("handles minimum value enforcement", () => {
      expect(formatTotalCost(0.001)).toBe("$0.01");
    });

    it("handles null/undefined values", () => {
      expect(formatTotalCost(null)).toBe("-");
      expect(formatTotalCost(undefined)).toBe("-");
    });

    it("handles string numbers", () => {
      expect(formatTotalCost("1.5")).toBe("$1.50");
    });
  });

  describe("formatDuration", () => {
    it("formats duration in seconds", () => {
      expect(formatDuration(1.234)).toBe("1.23s");
    });

    it("handles zero duration", () => {
      expect(formatDuration(0)).toBe("0.00s");
    });
  });

  describe("formatRelativeDate", () => {
    const now = new Date("2023-01-15T12:00:00Z");

    beforeEach(() => {
      jest.useFakeTimers();
      jest.setSystemTime(now);
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("handles null/undefined values", () => {
      expect(formatRelativeDate(null)).toBe("N/A");
      expect(formatRelativeDate(undefined)).toBe("N/A");
    });

    it("handles invalid dates", () => {
      expect(formatRelativeDate("invalid-date")).toBe("Invalid Date");
    });

    it('formats "just now" for very recent dates', () => {
      const recent = new Date("2023-01-15T11:59:30Z");
      expect(formatRelativeDate(recent.toISOString())).toBe("Just now");
    });

    it("formats minutes ago", () => {
      const minutesAgo = new Date("2023-01-15T11:45:00Z");
      expect(formatRelativeDate(minutesAgo.toISOString())).toBe("15m ago");
    });

    it("formats hours ago", () => {
      const hoursAgo = new Date("2023-01-15T10:00:00Z");
      expect(formatRelativeDate(hoursAgo.toISOString())).toBe("2h ago");
    });

    it("formats days ago", () => {
      const daysAgo = new Date("2023-01-13T12:00:00Z");
      expect(formatRelativeDate(daysAgo.toISOString())).toBe("2d ago");
    });

    it("formats older dates", () => {
      const oldDate = new Date("2023-01-01T12:00:00Z");
      expect(formatRelativeDate(oldDate.toISOString())).toBe("1/1/2023");
    });
  });
});

describe("Error-based Filtering Functions", () => {
  describe("shouldIncludeCostMetric", () => {
    it("returns true for valid cost", () => {
      const completion = mockExperimentCompletion(5, 10);
      expect(shouldIncludeCostMetric(completion)).toBe(true);
    });

    it("returns false for undefined completion", () => {
      expect(shouldIncludeCostMetric(undefined)).toBe(false);
    });

    it("returns false for zero cost with error", () => {
      const completion = {
        ...mockExperimentCompletion(0, 10),
        output: { error: { error: "Some error" }, messages: [] },
      };
      expect(shouldIncludeCostMetric(completion)).toBe(false);
    });

    it("returns true for zero cost without error", () => {
      const completion = mockExperimentCompletion(0, 10);
      expect(shouldIncludeCostMetric(completion)).toBe(true);
    });
  });

  describe("shouldIncludeDurationMetric", () => {
    it("returns true for valid duration", () => {
      const completion = mockExperimentCompletion(5, 10);
      expect(shouldIncludeDurationMetric(completion)).toBe(true);
    });

    it("returns false for undefined completion", () => {
      expect(shouldIncludeDurationMetric(undefined)).toBe(false);
    });

    it("returns false for zero duration with error", () => {
      const completion = {
        ...mockExperimentCompletion(5, 0),
        output: { error: { error: "Some error" }, messages: [] },
      };
      expect(shouldIncludeDurationMetric(completion)).toBe(false);
    });

    it("returns true for zero duration without error", () => {
      const completion = mockExperimentCompletion(5, 0);
      expect(shouldIncludeDurationMetric(completion)).toBe(true);
    });
  });

  describe("getValidCosts", () => {
    it("filters out invalid costs", () => {
      const completions = [
        mockExperimentCompletion(5, 10),
        { ...mockExperimentCompletion(0, 10), output: { error: { error: "Some error" }, messages: [] } },
        mockExperimentCompletion(3, 5),
        undefined,
      ];

      const result = getValidCosts(completions);
      expect(result).toEqual([5, 3]);
    });

    it("handles empty array", () => {
      expect(getValidCosts([])).toEqual([]);
    });
  });

  describe("getValidDurations", () => {
    it("filters out invalid durations", () => {
      const completions = [
        mockExperimentCompletion(5, 10),
        { ...mockExperimentCompletion(5, 0), output: { error: { error: "Some error" }, messages: [] } },
        mockExperimentCompletion(3, 7),
        undefined,
      ];

      const result = getValidDurations(completions);
      expect(result).toEqual([10, 7]);
    });

    it("handles empty array", () => {
      expect(getValidDurations([])).toEqual([]);
    });
  });
});

describe("Calculation Functions", () => {
  describe("calculateAverageMetrics", () => {
    it("handles empty completions array", () => {
      const result = calculateAverageMetrics([]);
      expect(result).toEqual({
        avgCost: undefined,
        avgDuration: undefined,
        costs: [],
        durations: [],
      });
    });

    it("calculates averages correctly", () => {
      const completions = [mockExperimentCompletion(1, 2), mockExperimentCompletion(3, 4)];

      const result = calculateAverageMetrics(completions);
      expect(result).toEqual({
        avgCost: 2,
        avgDuration: 3,
        costs: [1, 3],
        durations: [2, 4],
      });
    });

    it("handles null/undefined values", () => {
      const completions = [
        { ...mockExperimentCompletion(0, 0), cost_usd: 0, duration_seconds: 0 },
        mockExperimentCompletion(2, 4),
      ];

      const result = calculateAverageMetrics(completions);
      expect(result.avgCost).toBe(1); // (0 + 2) / 2
      expect(result.avgDuration).toBe(2); // (0 + 4) / 2
    });
  });
});

describe("Version Functions", () => {
  describe("getDifferingVersionKeys", () => {
    it("returns empty array for single version", () => {
      const result = getDifferingVersionKeys([mockVersion()]);
      expect(result).toEqual([]);
    });

    it("returns empty array for identical versions", () => {
      const versions = [mockVersion({ temperature: 0.5 }), mockVersion({ temperature: 0.5 })];
      const result = getDifferingVersionKeys(versions);
      expect(result).toEqual([]);
    });

    it("finds differing keys", () => {
      const versions = [
        mockVersion({ temperature: 0.5, max_tokens: 100 }),
        mockVersion({ temperature: 0.8, max_tokens: 100 }),
      ];
      const result = getDifferingVersionKeys(versions);
      expect(result).toContain("temperature");
      expect(result).not.toContain("max_tokens");
      expect(result).not.toContain("model"); // Always shown, so excluded
    });

    it("handles different value types", () => {
      const versions = [
        mockVersion({ tools: ["tool1"], stream: true }),
        mockVersion({ tools: ["tool2"], stream: false }),
      ];
      const result = getDifferingVersionKeys(versions);
      expect(result).toContain("tools");
      expect(result).toContain("stream");
    });
  });

  describe("getVersionKeyDisplayName", () => {
    it("returns display name for known keys", () => {
      expect(getVersionKeyDisplayName("temperature")).toBe("Temperature");
      expect(getVersionKeyDisplayName("output_schema")).toBe("Output Schema");
    });

    it("returns original key for unknown keys", () => {
      expect(getVersionKeyDisplayName("unknown_key")).toBe("unknown_key");
    });
  });

  describe("sortVersionKeys", () => {
    it("sorts keys according to predefined order", () => {
      const keys = ["temperature", "prompt", "model", "stop"];
      const result = sortVersionKeys(keys);
      expect(result).toEqual(["prompt", "temperature", "stop", "model"]);
    });

    it("handles unknown keys alphabetically at the end", () => {
      const keys = ["unknown2", "temperature", "unknown1"];
      const result = sortVersionKeys(keys);
      expect(result).toEqual(["temperature", "unknown1", "unknown2"]);
    });
  });

  describe("getVersionWithDefaults", () => {
    it("applies default values", () => {
      const version: Partial<Version> = { id: "1", model: "gpt-4" }; // Version without temperature, top_p, etc.
      const result = getVersionWithDefaults(version as Version);

      expect(result.temperature).toBe(1.0); // Should be the default value
      expect(result.top_p).toBe(1.0);
      expect(result.tools).toEqual([]);
      expect(result.use_cache).toBe("auto");
    });

    it("preserves existing values", () => {
      const version = mockVersion({ temperature: 0.5, tools: ["existing"] });
      const result = getVersionWithDefaults(version);

      expect(result.temperature).toBe(0.5);
      expect(result.tools).toEqual(["existing"]);
    });
  });
});

describe("Data Transformation Functions", () => {
  describe("parseJSONValue", () => {
    it("returns object as-is", () => {
      const obj = { key: "value" };
      expect(parseJSONValue(obj)).toBe(obj);
    });

    it("parses valid JSON string", () => {
      expect(parseJSONValue('{"key": "value"}')).toEqual({ key: "value" });
    });

    it("returns null for invalid JSON string", () => {
      expect(parseJSONValue("invalid json")).toBe(null);
    });

    it("returns null for non-string, non-object values", () => {
      expect(parseJSONValue(123)).toBe(null);
      expect(parseJSONValue(true)).toBe(null);
    });
  });

  describe("isDateValue", () => {
    it("identifies valid date strings", () => {
      expect(isDateValue("2023-01-15T12:00:00Z")).toBe(true);
      expect(isDateValue("2023-01-15")).toBe(true);
      expect(isDateValue("01/15/2023")).toBe(true);
    });

    it("rejects invalid date strings", () => {
      expect(isDateValue("not a date")).toBe(false);
      expect(isDateValue("123")).toBe(false);
      expect(isDateValue("abc")).toBe(false);
    });

    it("rejects non-string values", () => {
      expect(isDateValue(123)).toBe(false);
      expect(isDateValue({})).toBe(false);
    });
  });

  describe("transformCompletionsData", () => {
    it("merges input_messages and input_variables", () => {
      const data = [
        {
          id: "1",
          input_messages: '[{"role": "user", "content": "test"}]',
          input_variables: '{"var": "value"}',
          other: "data",
        },
      ];

      const result = transformCompletionsData(data);
      expect(result[0]).toHaveProperty("input");
      expect(result[0]).not.toHaveProperty("input_messages");
      expect(result[0]).not.toHaveProperty("input_variables");
      expect(result[0].other).toBe("data");

      const inputData = JSON.parse(result[0].input as string);
      expect(inputData).toHaveProperty("messages");
      expect(inputData).toHaveProperty("variables");
    });

    it("merges output_messages and output_error", () => {
      const data = [
        {
          output_messages: '[{"role": "assistant", "content": "response"}]',
          output_error: '{"error": "test error"}',
        },
      ];

      const result = transformCompletionsData(data);
      const outputData = JSON.parse(result[0].output as string);
      expect(outputData).toHaveProperty("messages");
      expect(outputData).toHaveProperty("error");
    });

    it("handles missing input/output fields", () => {
      const data = [{ id: "1", other: "data" }];
      const result = transformCompletionsData(data);
      expect(result[0]).toEqual({ id: "1", other: "data" });
    });
  });

  describe("transformToMultiSeriesChartData", () => {
    it("transforms data to multi-series format", () => {
      const data = [
        { date: "2023-01", cost: 10, model: "gpt-4" },
        { date: "2023-01", cost: 20, model: "gpt-3" },
        { date: "2023-02", cost: 15, model: "gpt-4" },
      ];

      const result = transformToMultiSeriesChartData(data, "date", "cost", "model");

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({ x: "2023-01", "gpt-4": 10, "gpt-3": 20 });
      expect(result[1]).toEqual({ x: "2023-02", "gpt-4": 15, "gpt-3": 0 });
    });

    it("handles empty data", () => {
      expect(transformToMultiSeriesChartData([], "x", "y", "series")).toEqual([]);
    });

    it("skips rows with missing required fields", () => {
      const data = [
        { date: "2023-01", cost: 10, model: "gpt-4" },
        { date: "", cost: 20, model: "gpt-3" }, // Missing date
        { date: "2023-02", cost: 30 }, // Missing model
      ];

      const result = transformToMultiSeriesChartData(data, "date", "cost", "model");
      expect(result).toHaveLength(1);
    });
  });
});

describe("Annotation Functions", () => {
  describe("filterAnnotations", () => {
    const annotations = [
      mockAnnotation({
        target: { completion_id: "comp1", key_path: "output.result" },
        context: { experiment_id: "exp1" },
      }),
      mockAnnotation({
        target: { completion_id: "comp2", experiment_id: "exp1" },
      }),
      mockAnnotation({
        target: { completion_id: "comp1", key_path: "input.message" },
      }),
    ];

    it("filters by completion ID", () => {
      const result = filterAnnotations(annotations, { completionId: "comp1" });
      expect(result).toHaveLength(2);
      expect(result.every((a) => a.target?.completion_id === "comp1")).toBe(true);
    });

    it("filters by experiment ID", () => {
      const result = filterAnnotations(annotations, { experimentId: "exp1" });
      expect(result).toHaveLength(2);
    });

    it("filters by key path", () => {
      const result = filterAnnotations(annotations, { keyPath: "output.result" });
      expect(result).toHaveLength(1);
    });

    it("filters by key path prefix", () => {
      const result = filterAnnotations(annotations, { keyPathPrefix: "output" });
      expect(result).toHaveLength(1);
    });

    it("combines multiple filters", () => {
      const result = filterAnnotations(annotations, {
        completionId: "comp1",
        keyPathPrefix: "output",
      });
      expect(result).toHaveLength(1);
    });

    it("handles undefined annotations", () => {
      const result = filterAnnotations(undefined, { completionId: "comp1" });
      expect(result).toEqual([]);
    });
  });
});

describe("JSON Schema Functions", () => {
  describe("resolveRef", () => {
    const rootSchema = {
      $defs: {
        TestType: {
          type: "object",
          properties: { name: { type: "string" } },
        },
      },
    };

    it("returns node as-is when no $ref", () => {
      const node = { type: "string" };
      expect(resolveRef(node, rootSchema)).toBe(node);
    });

    it("resolves internal reference", () => {
      const node = { $ref: "#/$defs/TestType" };
      const result = resolveRef(node, rootSchema);
      expect(result).toEqual(rootSchema.$defs.TestType);
    });

    it("handles invalid reference path", () => {
      const node = { $ref: "#/$defs/NonExistent" };
      const result = resolveRef(node, rootSchema);
      expect(result).toBe(node); // Returns original on failure
    });

    it("handles unsupported reference format", () => {
      const node = { $ref: "http://example.com/schema" };
      const result = resolveRef(node, rootSchema);
      expect(result).toBe(node);
    });
  });
});

describe("Text Processing Functions", () => {
  describe("stripMarkdown", () => {
    it("removes headers", () => {
      expect(stripMarkdown("# Header 1\n## Header 2")).toBe("Header 1 Header 2");
    });

    it("removes bold formatting", () => {
      expect(stripMarkdown("**bold text**")).toBe("bold text");
    });

    it("removes italic formatting", () => {
      expect(stripMarkdown("*italic text*")).toBe("italic text");
    });

    it("removes inline code", () => {
      expect(stripMarkdown("`code`")).toBe("code");
    });

    it("removes links but keeps text", () => {
      expect(stripMarkdown("[link text](http://example.com)")).toBe("link text");
    });

    it("removes blockquotes", () => {
      expect(stripMarkdown("> quoted text")).toBe("quoted text");
    });

    it("removes list markers", () => {
      expect(stripMarkdown("- item 1\n* item 2\n+ item 3")).toBe("item 1 item 2 item 3");
    });

    it("removes numbered list markers", () => {
      expect(stripMarkdown("1. first\n2. second")).toBe("first second");
    });

    it("handles complex markdown", () => {
      const markdown = `
# Title
This is **bold** and *italic* text with \`code\` and [a link](http://example.com).

> A quote

- List item 1
- List item 2

1. Numbered item
2. Another item
      `;

      const result = stripMarkdown(markdown);
      expect(result).toContain("Title");
      expect(result).toContain("bold");
      expect(result).toContain("italic");
      expect(result).toContain("code");
      expect(result).toContain("a link");
      expect(result).not.toContain("**");
      expect(result).not.toContain("*");
      expect(result).not.toContain("`");
      expect(result).not.toContain("[");
      expect(result).not.toContain(">");
      expect(result).not.toContain("-");
      expect(result).not.toContain("1.");
    });
  });
});

describe("Prompt Functions", () => {
  describe("getSharedPartsOfPrompts", () => {
    // Mock data from the experiment - simplified versions for testing
    const mockVersions: Version[] = [
      {
        id: "d7b096502a66ce3d97c1314f4ea45d79",
        model: "llama4-maverick-instruct-fast",
        temperature: 0.0,
        top_p: 1.0,
        prompt: [
          {
            role: "system",
            content:
              "Extract meeting notes from the provided transcript and any additional user notes if provided.\n\nOrganize the notes by topics discussed.\n\nFor each topic, create an object with:\n\n- a 'title' property representing the topic name.\n- a 'bullets' property containing a maximum of 5 bullet points summarizing the main ideas regarding the topic. Be strict here, try to avoid overlap between topics.\n\nEach bullet point should be a short, digestible sentence without pronouns unless explicitly defined.\n\nFormat the bullet points as a string with each point on a new line, preceded by a hyphen and space.\n\nExample bullet format:\n- Point 1\n- Point 2\n- Point 3\n- Point 4\n- Point 5.\n\nEnsure all sentences are decontextualized and can stand alone without reference to other parts of the conversation.",
          },
          {
            role: "user",
            content: "user_notes: {{user_notes}}\n\ntranscript: {{transcript}}",
          },
        ],
      },
      {
        id: "218d13d8e9458d94311dc64860adf3fb",
        model: "gpt-4o-mini-2024-07-18",
        temperature: 0.0,
        top_p: 1.0,
        prompt: [
          {
            role: "system",
            content:
              "Extract meeting notes from the provided transcript and any additional user notes if provided.\n\nOrganize the notes by topics discussed.\n\nFor each topic, create an object with:\n\n- a 'title' property representing the topic name.\n- a 'bullets' property containing a maximum of 5 bullet points summarizing the main ideas regarding the topic. Be strict here, try to avoid overlap between topics.\n\nEach bullet point should be a short, digestible sentence without pronouns unless explicitly defined.\n\nFormat the bullet points as a string with each point on a new line, preceded by a hyphen and space.\n\nExample bullet format:\n- Point 1\n- Point 2\n- Point 3\n- Point 4\n- Point 5.\n\nEnsure all sentences are decontextualized and can stand alone without reference to other parts of the conversation.",
          },
          {
            role: "user",
            content: "user_notes: {{user_notes}}\n\ntranscript: {{transcript}}",
          },
        ],
      },
      {
        id: "f9c91ed3b3f58d9821959517434f463e",
        model: "llama4-maverick-instruct-fast",
        temperature: 0.0,
        top_p: 1.0,
        prompt: [
          {
            role: "system",
            content:
              'Extract meeting notes from the provided transcript and any additional user notes if provided.\n\nIMPORTANT: \n- If the transcript is empty or contains no meaningful conversation, return an empty meeting_notes array.\n- Do NOT generate fictional content if no actual meeting or conversation occurred.\n- Only extract notes if there\'s substantive business discussion.\n\nExamples of when to return empty meeting_notes:\n- Empty transcript\n- Single greetings only ("hello", "hi")\n- Personal conversations (family dinner plans, personal favors)\n- Brief coordination calls ("I\'m 4 minutes away", "meet me in the parking lot")\n- Technical issues with no actual discussion\n\nOrganize the notes by topics discussed.\n\nFor each topic, create an object with:\n\n- a \'title\' property representing the topic name.\n- a \'bullets\' property containing a maximum of 5 bullet points summarizing the main ideas regarding the topic. Be strict here, try to avoid overlap between topics.\n\nEach bullet point should be a short, digestible sentence without pronouns unless explicitly defined.\n\nFormat the bullet points as a string with each point on a new line, preceded by a hyphen and space.\n\nExample bullet format:\n- Point 1\n- Point 2\n- Point 3\n- Point 4\n- Point 5.\n\nEnsure all sentences are decontextualized and can stand alone without reference to other parts of the conversation.',
          },
          {
            role: "user",
            content: "user_notes: {{user_notes}}\n\ntranscript: {{transcript}}",
          },
        ],
      },
    ];

    it("returns empty array for empty versions", () => {
      expect(getSharedPartsOfPrompts([])).toEqual([]);
    });

    it("returns empty array for versions without prompts", () => {
      const versionsWithoutPrompts: Version[] = [
        {
          id: "1",
          model: "gpt-4",
          temperature: 0.0,
          top_p: 1.0,
        },
      ];
      expect(getSharedPartsOfPrompts(versionsWithoutPrompts)).toEqual([]);
    });

    it("returns the prompt for single version with prompts", () => {
      const singleVersion: Version[] = [mockVersions[0]];
      const result = getSharedPartsOfPrompts(singleVersion);
      expect(result).toEqual(mockVersions[0].prompt);
    });

    it("finds shared content across multiple versions", () => {
      const result = getSharedPartsOfPrompts(mockVersions);

      // Should find shared system message content
      expect(result).toHaveLength(2); // system and user roles

      const systemMessage = result.find((msg) => msg.role === "system");
      const userMessage = result.find((msg) => msg.role === "user");

      expect(systemMessage).toBeDefined();
      expect(userMessage).toBeDefined();

      // Check that shared content includes common parts
      expect(systemMessage?.content).toContain("Extract meeting notes");
      expect(systemMessage?.content).toContain("Organize the notes by topics");
      expect(systemMessage?.content).toContain("title' property representing the topic name");
      expect(systemMessage?.content).toContain("bullets' property containing a maximum of 5 bullet points");

      // User message should be identical across versions
      expect(userMessage?.content).toBe("user_notes: {{user_notes}}\n\ntranscript: {{transcript}}");
    });

    it("handles versions with different prompt lengths", () => {
      const differentLengthVersions: Version[] = [
        {
          id: "1",
          model: "gpt-4",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [{ role: "system", content: "Common system prompt" }],
        },
        {
          id: "2",
          model: "gpt-3.5",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [
            { role: "system", content: "Common system prompt" },
            { role: "user", content: "Additional user prompt" },
          ],
        },
      ];

      const result = getSharedPartsOfPrompts(differentLengthVersions);
      expect(result).toHaveLength(1);
      expect(result[0].role).toBe("system");
      expect(result[0].content).toBe("Common system prompt");
    });

    it("handles array content in messages", () => {
      const versionsWithArrayContent: Version[] = [
        {
          id: "1",
          model: "gpt-4",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [
            {
              role: "user",
              content: [{ text: "First part of message" }, { text: "Second part of message" }],
            },
          ],
        },
        {
          id: "2",
          model: "gpt-3.5",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [
            {
              role: "user",
              content: [{ text: "First part of message" }, { text: "Different second part" }],
            },
          ],
        },
      ];

      const result = getSharedPartsOfPrompts(versionsWithArrayContent);
      expect(result).toHaveLength(1);
      expect(result[0].role).toBe("user");
      expect(result[0].content).toContain("First part of message");
    });

    it("handles empty or whitespace-only content", () => {
      const versionsWithEmptyContent: Version[] = [
        {
          id: "1",
          model: "gpt-4",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [
            { role: "system", content: "" },
            { role: "user", content: "Real content" },
          ],
        },
        {
          id: "2",
          model: "gpt-3.5",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [
            { role: "system", content: "   " },
            { role: "user", content: "Real content" },
          ],
        },
      ];

      const result = getSharedPartsOfPrompts(versionsWithEmptyContent);
      expect(result).toHaveLength(1);
      expect(result[0].role).toBe("user");
      expect(result[0].content).toBe("Real content");
    });

    it("handles versions where not all have the same role at the same position", () => {
      const versionsWithMissingRoles: Version[] = [
        {
          id: "1",
          model: "gpt-4",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [
            { role: "system", content: "System message" },
            { role: "user", content: "User message" },
          ],
        },
        {
          id: "2",
          model: "gpt-3.5",
          temperature: 0.0,
          top_p: 1.0,
          prompt: [{ role: "user", content: "Different user message" }],
        },
      ];

      const result = getSharedPartsOfPrompts(versionsWithMissingRoles);
      // Should only include roles that appear at the same position across ALL versions
      expect(result).toHaveLength(0);
    });
  });
});
