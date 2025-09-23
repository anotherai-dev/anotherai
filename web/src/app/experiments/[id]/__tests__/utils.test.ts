import { Annotation, ExperimentWithLookups } from "@/types/models";
import {
  findAllMetricKeysAndAverages,
  getAllMetricsPerKey,
  getAllMetricsPerKeyForRow,
  getMetricsForCompletion,
  getMetricsPerVersion,
} from "../utils";

// Mock types for testing
const mockAnnotation = (overrides: Record<string, unknown> = {}) => ({
  id: "1",
  created_at: "2023-01-01T00:00:00Z",
  author_name: "test-user",
  target: {},
  context: {},
  metric: undefined,
  ...overrides,
});

const mockExperimentCompletion = (id: string, inputId: string, versionId: string) => ({
  id,
  input: { id: inputId },
  version: { id: versionId },
  cost_usd: 0.1,
  duration_seconds: 1.5,
});

const mockExperiment = (completions: unknown[] = [], versions: unknown[] = []) => ({
  id: "exp1",
  completions,
  versions,
});

describe("Experiment Utilities", () => {
  describe("findAllMetricKeysAndAverages", () => {
    it("returns empty array for empty annotations", () => {
      const result = findAllMetricKeysAndAverages([]);
      expect(result).toEqual([]);
    });

    it("ignores annotations without metrics", () => {
      const annotations = [mockAnnotation({ metric: undefined }), mockAnnotation({ metric: undefined }), mockAnnotation({})];
      const result = findAllMetricKeysAndAverages(annotations);
      expect(result).toEqual([]);
    });

    it("ignores non-numeric metric values", () => {
      const annotations = [
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        mockAnnotation({ metric: { name: "accuracy", value: "high" as any } }),
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        mockAnnotation({ metric: { name: "quality", value: null as any } }),
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        mockAnnotation({ metric: { name: "score", value: undefined as any } }),
      ];
      const result = findAllMetricKeysAndAverages(annotations);
      expect(result).toEqual([]);
    });

    it("calculates average for single metric", () => {
      const annotations = [
        mockAnnotation({ metric: { name: "accuracy", value: 0.8 } }),
        mockAnnotation({ metric: { name: "accuracy", value: 0.9 } }),
        mockAnnotation({ metric: { name: "accuracy", value: 0.7 } }),
      ];
      const result = findAllMetricKeysAndAverages(annotations);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        key: "accuracy",
        average: 0.8, // (0.8 + 0.9 + 0.7) / 3
      });
    });

    it("calculates averages for multiple metrics", () => {
      const annotations = [
        mockAnnotation({ metric: { name: "accuracy", value: 0.8 } }),
        mockAnnotation({ metric: { name: "precision", value: 0.9 } }),
        mockAnnotation({ metric: { name: "accuracy", value: 0.6 } }),
        mockAnnotation({ metric: { name: "precision", value: 0.7 } }),
      ];
      const result = findAllMetricKeysAndAverages(annotations);

      expect(result).toHaveLength(2);

      const accuracyMetric = result.find((m) => m.key === "accuracy");
      const precisionMetric = result.find((m) => m.key === "precision");

      expect(accuracyMetric).toEqual({ key: "accuracy", average: 0.7 });
      expect(precisionMetric).toEqual({ key: "precision", average: 0.8 });
    });

    it("sorts results by metric key alphabetically", () => {
      const annotations = [
        mockAnnotation({ metric: { name: "zebra", value: 1 } }),
        mockAnnotation({ metric: { name: "alpha", value: 2 } }),
        mockAnnotation({ metric: { name: "beta", value: 3 } }),
      ];
      const result = findAllMetricKeysAndAverages(annotations);

      expect(result.map((m) => m.key)).toEqual(["alpha", "beta", "zebra"]);
    });

    it("rounds averages to 2 decimal places", () => {
      const annotations = [
        mockAnnotation({ metric: { name: "score", value: 0.333333 } }),
        mockAnnotation({ metric: { name: "score", value: 0.666666 } }),
      ];
      const result = findAllMetricKeysAndAverages(annotations);

      expect(result[0].average).toBe(0.5);
    });

    it("handles edge case with very small numbers", () => {
      const annotations = [
        mockAnnotation({ metric: { name: "error_rate", value: 0.0001 } }),
        mockAnnotation({ metric: { name: "error_rate", value: 0.0002 } }),
      ];
      const result = findAllMetricKeysAndAverages(annotations);

      expect(result[0].average).toBe(0);
    });
  });

  describe("getMetricsPerVersion", () => {
    const completions = [
      mockExperimentCompletion("comp1", "input1", "version1"),
      mockExperimentCompletion("comp2", "input2", "version1"),
      mockExperimentCompletion("comp3", "input1", "version2"),
    ];

    const versions = [{ id: "version1" }, { id: "version2" }];

    const experiment = mockExperiment(completions, versions);

    it("returns undefined when no annotations provided", () => {
      const result = getMetricsPerVersion(experiment as ExperimentWithLookups);
      expect(result).toBeUndefined();
    });

    it("returns undefined for undefined annotations", () => {
      const result = getMetricsPerVersion(experiment as ExperimentWithLookups, undefined);
      expect(result).toBeUndefined();
    });

    it("groups annotations by version correctly", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "accuracy", value: 0.8 },
        }),
        mockAnnotation({
          target: { completion_id: "comp2" },
          metric: { name: "accuracy", value: 0.9 },
        }),
        mockAnnotation({
          target: { completion_id: "comp3" },
          metric: { name: "accuracy", value: 0.7 },
        }),
      ];

      const result = getMetricsPerVersion(experiment as ExperimentWithLookups, annotations);

      expect(result).toBeDefined();
      expect(result!["version1"]).toHaveLength(1);
      expect(result!["version1"][0]).toEqual({ key: "accuracy", average: 0.85 });
      expect(result!["version2"]).toHaveLength(1);
      expect(result!["version2"][0]).toEqual({ key: "accuracy", average: 0.7 });
    });

    it("handles versions with no matching annotations", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "nonexistent" },
          metric: { name: "accuracy", value: 0.8 },
        }),
      ];

      const result = getMetricsPerVersion(experiment as ExperimentWithLookups, annotations);

      expect(result!["version1"]).toEqual([]);
      expect(result!["version2"]).toEqual([]);
    });

    it("handles annotations without completion_id", () => {
      const annotations = [
        mockAnnotation({
          target: {},
          metric: { name: "accuracy", value: 0.8 },
        }),
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "precision", value: 0.9 },
        }),
      ];

      const result = getMetricsPerVersion(experiment as ExperimentWithLookups, annotations);

      expect(result!["version1"]).toHaveLength(1);
      expect(result!["version1"][0].key).toBe("precision");
    });
  });

  describe("getAllMetricsPerKey", () => {
    it("returns undefined for undefined input", () => {
      const result = getAllMetricsPerKey(undefined);
      expect(result).toBeUndefined();
    });

    it("extracts all metric values per key", () => {
      const metricsPerVersion = {
        version1: [
          { key: "accuracy", average: 0.8 },
          { key: "precision", average: 0.9 },
        ],
        version2: [
          { key: "accuracy", average: 0.7 },
          { key: "recall", average: 0.85 },
        ],
      };

      const result = getAllMetricsPerKey(metricsPerVersion);

      expect(result).toEqual({
        accuracy: [0.8, 0.7],
        precision: [0.9],
        recall: [0.85],
      });
    });

    it("handles empty metrics per version", () => {
      const metricsPerVersion = {
        version1: [],
        version2: [{ key: "accuracy", average: 0.8 }],
      };

      const result = getAllMetricsPerKey(metricsPerVersion);

      expect(result).toEqual({
        accuracy: [0.8],
      });
    });

    it("collects all instances of same metric key", () => {
      const metricsPerVersion = {
        version1: [{ key: "score", average: 0.8 }],
        version2: [{ key: "score", average: 0.7 }],
        version3: [{ key: "score", average: 0.9 }],
      };

      const result = getAllMetricsPerKey(metricsPerVersion);

      expect(result!["score"]).toEqual([0.8, 0.7, 0.9]);
    });
  });

  describe("getMetricsForCompletion", () => {
    it("returns empty array when no annotations match", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "other" },
          metric: { name: "accuracy", value: 0.8 },
        }),
      ];

      const result = getMetricsForCompletion(annotations, "target_completion");
      expect(result).toEqual([]);
    });

    it("filters annotations for specific completion", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "accuracy", value: 0.8 },
        }),
        mockAnnotation({
          target: { completion_id: "comp2" },
          metric: { name: "accuracy", value: 0.9 },
        }),
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "precision", value: 0.7 },
        }),
      ];

      const result = getMetricsForCompletion(annotations, "comp1");

      expect(result).toHaveLength(2);
      expect(result.find((m) => m.key === "accuracy")?.average).toBe(0.8);
      expect(result.find((m) => m.key === "precision")?.average).toBe(0.7);
    });

    it("ignores annotations without metrics", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: undefined,
        }),
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "accuracy", value: 0.8 },
        }),
      ];

      const result = getMetricsForCompletion(annotations, "comp1");

      expect(result).toHaveLength(1);
      expect(result[0].key).toBe("accuracy");
    });
  });

  describe("getAllMetricsPerKeyForRow", () => {
    const completions = [
      mockExperimentCompletion("comp1", "input1", "version1"),
      mockExperimentCompletion("comp2", "input1", "version2"),
      mockExperimentCompletion("comp3", "input2", "version1"),
    ];

    const versions = [{ id: "version1" }, { id: "version2" }];

    const experiment = mockExperiment(completions, versions);

    it("returns undefined when no annotations provided", () => {
      const result = getAllMetricsPerKeyForRow(experiment as ExperimentWithLookups, undefined, "input1");
      expect(result).toBeUndefined();
    });

    it("groups metrics by key for specific input row", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "accuracy", value: 0.8 },
        }),
        mockAnnotation({
          target: { completion_id: "comp2" },
          metric: { name: "accuracy", value: 0.7 },
        }),
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "precision", value: 0.9 },
        }),
        // This should be ignored (different input)
        mockAnnotation({
          target: { completion_id: "comp3" },
          metric: { name: "accuracy", value: 0.6 },
        }),
      ];

      const result = getAllMetricsPerKeyForRow(experiment as ExperimentWithLookups, annotations, "input1");

      expect(result).toEqual({
        accuracy: [0.8, 0.7],
        precision: [0.9],
      });
    });

    it("handles input with completions across multiple versions", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "score", value: 0.8 },
        }),
        mockAnnotation({
          target: { completion_id: "comp2" },
          metric: { name: "score", value: 0.9 },
        }),
      ];

      const result = getAllMetricsPerKeyForRow(experiment as ExperimentWithLookups, annotations, "input1");

      expect(result!["score"]).toEqual([0.8, 0.9]);
    });

    it("handles input with no completions", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "accuracy", value: 0.8 },
        }),
      ];

      const result = getAllMetricsPerKeyForRow(experiment as ExperimentWithLookups, annotations, "nonexistent_input");

      expect(result).toEqual({});
    });

    it("handles completions without annotations", () => {
      const annotations: Annotation[] = [];

      const result = getAllMetricsPerKeyForRow(experiment as ExperimentWithLookups, annotations, "input1");

      expect(result).toEqual({});
    });

    it("filters completions correctly by input ID", () => {
      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "accuracy", value: 0.8 },
        }),
        mockAnnotation({
          target: { completion_id: "comp3" },
          metric: { name: "accuracy", value: 0.6 },
        }),
      ];

      // Should only include comp1 (input1), not comp3 (input2)
      const result = getAllMetricsPerKeyForRow(experiment as ExperimentWithLookups, annotations, "input1");

      expect(result!["accuracy"]).toEqual([0.8]);
    });
  });

  describe("Integration scenarios", () => {
    it("handles complete workflow from annotations to per-key metrics", () => {
      const completions = [
        mockExperimentCompletion("comp1", "input1", "version1"),
        mockExperimentCompletion("comp2", "input1", "version2"),
      ];

      const versions = [{ id: "version1" }, { id: "version2" }];
      const experiment = mockExperiment(completions, versions);

      const annotations = [
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "accuracy", value: 0.8 },
        }),
        mockAnnotation({
          target: { completion_id: "comp1" },
          metric: { name: "precision", value: 0.9 },
        }),
        mockAnnotation({
          target: { completion_id: "comp2" },
          metric: { name: "accuracy", value: 0.7 },
        }),
      ];

      // Test full workflow
      const metricsPerVersion = getMetricsPerVersion(experiment as ExperimentWithLookups, annotations);
      const allMetricsPerKey = getAllMetricsPerKey(metricsPerVersion);
      const rowMetrics = getAllMetricsPerKeyForRow(experiment as ExperimentWithLookups, annotations, "input1");

      expect(metricsPerVersion!["version1"]).toHaveLength(2);
      expect(metricsPerVersion!["version2"]).toHaveLength(1);

      expect(allMetricsPerKey!["accuracy"]).toEqual([0.8, 0.7]);
      expect(allMetricsPerKey!["precision"]).toEqual([0.9]);

      expect(rowMetrics!["accuracy"]).toEqual([0.8, 0.7]);
      expect(rowMetrics!["precision"]).toEqual([0.9]);
    });

    it("handles complex multi-metric, multi-version scenario", () => {
      const completions = [
        mockExperimentCompletion("comp1", "input1", "version1"),
        mockExperimentCompletion("comp2", "input2", "version1"),
        mockExperimentCompletion("comp3", "input1", "version2"),
        mockExperimentCompletion("comp4", "input2", "version2"),
      ];

      const versions = [{ id: "version1" }, { id: "version2" }];
      const experiment = mockExperiment(completions, versions);

      const annotations = [
        // Version 1 metrics
        mockAnnotation({ target: { completion_id: "comp1" }, metric: { name: "accuracy", value: 0.8 } }),
        mockAnnotation({ target: { completion_id: "comp1" }, metric: { name: "speed", value: 1.2 } }),
        mockAnnotation({ target: { completion_id: "comp2" }, metric: { name: "accuracy", value: 0.85 } }),

        // Version 2 metrics
        mockAnnotation({ target: { completion_id: "comp3" }, metric: { name: "accuracy", value: 0.75 } }),
        mockAnnotation({ target: { completion_id: "comp3" }, metric: { name: "quality", value: 4.5 } }),
        mockAnnotation({ target: { completion_id: "comp4" }, metric: { name: "accuracy", value: 0.9 } }),
      ];

      const metricsPerVersion = getMetricsPerVersion(experiment as ExperimentWithLookups, annotations);

      expect(metricsPerVersion!["version1"]).toHaveLength(2);
      expect(metricsPerVersion!["version1"].find((m) => m.key === "accuracy")?.average).toBe(0.82); // (0.8 + 0.85) / 2 = 0.825, rounded to 0.82
      expect(metricsPerVersion!["version1"].find((m) => m.key === "speed")?.average).toBe(1.2);

      expect(metricsPerVersion!["version2"]).toHaveLength(2);
      expect(metricsPerVersion!["version2"].find((m) => m.key === "accuracy")?.average).toBe(0.82); // (0.75 + 0.9) / 2 = 0.825, rounded to 0.82
      expect(metricsPerVersion!["version2"].find((m) => m.key === "quality")?.average).toBe(4.5);
    });
  });
});
