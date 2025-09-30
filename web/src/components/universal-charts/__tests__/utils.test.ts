import {
  DEFAULT_CHART_COLORS,
  SeriesConfig,
  autoDetectSeries,
  ensureXFieldForChart,
  transformDataForCompletionsGraph,
} from "../utils";

describe("Chart Utilities", () => {
  describe("DEFAULT_CHART_COLORS", () => {
    it("contains expected number of colors", () => {
      expect(DEFAULT_CHART_COLORS).toHaveLength(40);
    });

    it("contains valid hex colors", () => {
      DEFAULT_CHART_COLORS.forEach((color) => {
        expect(color).toMatch(/^#[0-9a-fA-F]{6}$/);
      });
    });

    it("starts with expected primary colors", () => {
      expect(DEFAULT_CHART_COLORS[0]).toBe("#3b82f6"); // Blue
      expect(DEFAULT_CHART_COLORS[1]).toBe("#ef4444"); // Red
      expect(DEFAULT_CHART_COLORS[2]).toBe("#10b981"); // Green
    });

    it("has unique colors", () => {
      const uniqueColors = new Set(DEFAULT_CHART_COLORS);
      expect(uniqueColors.size).toBe(DEFAULT_CHART_COLORS.length);
    });
  });

  describe("autoDetectSeries", () => {
    describe("Input validation", () => {
      it("returns provided series if available", () => {
        const providedSeries: SeriesConfig[] = [{ key: "custom", color: "#000000", name: "Custom Series" }];
        const data = [{ x: "2023", y: 100 }];

        const result = autoDetectSeries(data, providedSeries);
        expect(result).toBe(providedSeries);
      });

      it("returns empty array for empty data", () => {
        const result = autoDetectSeries([]);
        expect(result).toEqual([]);
      });

      it("returns empty array when data has y field (single series)", () => {
        const data = [{ x: "2023", y: 100 }];
        const result = autoDetectSeries(data);
        expect(result).toEqual([]);
      });

      it("returns empty array when no series keys exist", () => {
        const data = [{ x: "2023" }]; // Only x field
        const result = autoDetectSeries(data);
        expect(result).toEqual([]);
      });
    });

    describe("Series detection", () => {
      it("detects single series from multi-series data", () => {
        const data = [{ x: "2023", revenue: 100 }];
        const result = autoDetectSeries(data);

        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({
          key: "revenue",
          color: DEFAULT_CHART_COLORS[0],
          name: "revenue",
        });
      });

      it("detects multiple series from multi-series data", () => {
        const data = [
          {
            x: "2023",
            revenue: 100,
            expenses: 50,
            profit: 50,
          },
        ];
        const result = autoDetectSeries(data);

        expect(result).toHaveLength(3);
        expect(result[0]).toEqual({
          key: "revenue",
          color: DEFAULT_CHART_COLORS[0],
          name: "revenue",
        });
        expect(result[1]).toEqual({
          key: "expenses",
          color: DEFAULT_CHART_COLORS[1],
          name: "expenses",
        });
        expect(result[2]).toEqual({
          key: "profit",
          color: DEFAULT_CHART_COLORS[2],
          name: "profit",
        });
      });

      it("excludes x and y fields from series detection", () => {
        const data = [
          {
            x: "2023",
            y: 200, // Should be excluded due to y field presence - returns empty array
            revenue: 100,
            expenses: 50,
          },
        ];
        const result = autoDetectSeries(data);

        expect(result).toHaveLength(0); // Returns empty when y field is present
      });

      it("handles large number of series with color cycling", () => {
        const data: Record<string, unknown> = { x: "2023" };

        // Create more series than available colors
        for (let i = 0; i < 60; i++) {
          data[`series${i}`] = i * 10;
        }

        const result = autoDetectSeries([data]);
        expect(result).toHaveLength(60);

        // Check color cycling
        expect(result[0].color).toBe(DEFAULT_CHART_COLORS[0]);
        expect(result[40].color).toBe(DEFAULT_CHART_COLORS[0]); // Cycles back (array has 40 items)
        expect(result[41].color).toBe(DEFAULT_CHART_COLORS[1]);
      });
    });

    describe("Series configuration", () => {
      it("creates series with correct structure", () => {
        const data = [{ x: "2023", metric: 100 }];
        const result = autoDetectSeries(data);

        expect(result[0]).toHaveProperty("key");
        expect(result[0]).toHaveProperty("color");
        expect(result[0]).toHaveProperty("name");

        expect(typeof result[0].key).toBe("string");
        expect(typeof result[0].color).toBe("string");
        expect(typeof result[0].name).toBe("string");
      });

      it("uses key as name by default", () => {
        const data = [{ x: "2023", user_count: 100 }];
        const result = autoDetectSeries(data);

        expect(result[0].key).toBe("user_count");
        expect(result[0].name).toBe("user_count");
      });

      it("assigns colors in order", () => {
        const data = [
          {
            x: "2023",
            first: 1,
            second: 2,
            third: 3,
          },
        ];
        const result = autoDetectSeries(data);

        expect(result[0].color).toBe(DEFAULT_CHART_COLORS[0]);
        expect(result[1].color).toBe(DEFAULT_CHART_COLORS[1]);
        expect(result[2].color).toBe(DEFAULT_CHART_COLORS[2]);
      });
    });

    describe("Edge cases", () => {
      it("handles data with mixed field types", () => {
        const data = [
          {
            x: "2023",
            stringField: "text",
            numberField: 100,
            booleanField: true,
            nullField: null,
            undefinedField: undefined,
          },
        ];
        const result = autoDetectSeries(data);

        // Should include all non-x fields
        expect(result).toHaveLength(5);
        expect(result.map((s) => s.key)).toContain("stringField");
        expect(result.map((s) => s.key)).toContain("numberField");
        expect(result.map((s) => s.key)).toContain("booleanField");
        expect(result.map((s) => s.key)).toContain("nullField");
        expect(result.map((s) => s.key)).toContain("undefinedField");
      });

      it("handles data with nested objects", () => {
        const data = [
          {
            x: "2023",
            simple: 100,
            nested: { value: 50 },
            array: [1, 2, 3],
          },
        ];
        const result = autoDetectSeries(data);

        expect(result).toHaveLength(3);
        expect(result.map((s) => s.key)).toContain("simple");
        expect(result.map((s) => s.key)).toContain("nested");
        expect(result.map((s) => s.key)).toContain("array");
      });

      it("handles empty series keys scenario", () => {
        const data = [{ x: "2023" }]; // Only x field, no series
        const result = autoDetectSeries(data);
        expect(result).toEqual([]);
      });

      it("handles data with numeric keys", () => {
        const data = [
          {
            x: "2023",
            "2022": 100, // Numeric string key
            "2023": 150,
          },
        ];
        const result = autoDetectSeries(data);

        expect(result).toHaveLength(2);
        expect(result.map((s) => s.key)).toContain("2022");
        expect(result.map((s) => s.key)).toContain("2023");
      });
    });

    describe("Consistency", () => {
      it("maintains consistent order across calls with same data", () => {
        const data = [
          {
            x: "2023",
            charlie: 3,
            alpha: 1,
            bravo: 2,
          },
        ];

        const result1 = autoDetectSeries(data);
        const result2 = autoDetectSeries(data);

        expect(result1.map((s) => s.key)).toEqual(result2.map((s) => s.key));
        expect(result1.map((s) => s.color)).toEqual(result2.map((s) => s.color));
      });

      it("handles different data structures consistently", () => {
        const data1 = [{ x: "A", series1: 1, series2: 2 }];
        const data2 = [{ x: "B", series1: 3, series2: 4 }];

        const result1 = autoDetectSeries(data1);
        const result2 = autoDetectSeries(data2);

        // Should detect same series structure
        expect(result1.map((s) => s.key)).toEqual(result2.map((s) => s.key));
        expect(result1.map((s) => s.color)).toEqual(result2.map((s) => s.color));
      });
    });

    describe("Performance considerations", () => {
      it("handles large datasets efficiently", () => {
        const largeData: Record<string, unknown>[] = [];

        // Create dataset with 1000 rows and 20 series
        for (let i = 0; i < 1000; i++) {
          const row: Record<string, unknown> = { x: `item${i}` };
          for (let j = 0; j < 20; j++) {
            row[`metric${j}`] = Math.random() * 100;
          }
          largeData.push(row);
        }

        const startTime = performance.now();
        const result = autoDetectSeries(largeData);
        const endTime = performance.now();

        expect(result).toHaveLength(20);
        expect(endTime - startTime).toBeLessThan(100); // Should complete quickly
      });

      it("only examines first row for series detection", () => {
        const data = [
          { x: "2023", series1: 1, series2: 2 },
          { x: "2024", series1: 3, series3: 4 }, // series3 only in second row
        ];

        const result = autoDetectSeries(data);

        // Should only detect series from first row
        expect(result).toHaveLength(2);
        expect(result.map((s) => s.key)).toContain("series1");
        expect(result.map((s) => s.key)).toContain("series2");
        expect(result.map((s) => s.key)).not.toContain("series3");
      });
    });
  });

  describe("ensureXFieldForChart", () => {
    it("should transform data with date field to use x field", () => {
      const data = [
        { date: "2025-09-03", actor_movies_cost: 0.6567310000000002, movie_similarity_cost: 0.0 },
        { date: "2025-09-04", actor_movies_cost: 0.020062, movie_similarity_cost: 0.0 },
        { date: "2025-09-08", actor_movies_cost: 0.014131999999999999, movie_similarity_cost: 0.097382 },
      ];

      const result = ensureXFieldForChart(data);

      expect(result[0]).toHaveProperty("x", "2025-09-03");
      expect(result[0]).toHaveProperty("date", "2025-09-03");
      expect(result[0]).toHaveProperty("actor_movies_cost", 0.6567310000000002);
      expect(result[0]).toHaveProperty("movie_similarity_cost", 0.0);
    });

    it("should detect multiple series from date-based data", () => {
      const data = [
        { date: "2025-09-03", actor_movies_cost: 0.6567310000000002, movie_similarity_cost: 0.0 },
        { date: "2025-09-04", actor_movies_cost: 0.020062, movie_similarity_cost: 0.0 },
      ];

      const transformedData = ensureXFieldForChart(data);
      const series = autoDetectSeries(transformedData);

      expect(series).toHaveLength(2);
      expect(series.map((s) => s.key)).toContain("actor_movies_cost");
      expect(series.map((s) => s.key)).toContain("movie_similarity_cost");
      expect(series.map((s) => s.key)).not.toContain("date");
    });

    it("should handle data that already has x field", () => {
      const data = [{ x: "test", value: 123 }];

      const result = ensureXFieldForChart(data);

      expect(result).toBe(data); // Should return same reference if x already exists
    });

    it("should handle empty data", () => {
      const result = ensureXFieldForChart([]);

      expect(result).toEqual([]);
    });
  });

  describe("transformDataForCompletionsGraph", () => {
    it("should handle multi-series data with date field", () => {
      const data = [
        { date: "2025-09-03", actor_movies_cost: 0.6567310000000002, movie_similarity_cost: 0.0 },
        { date: "2025-09-04", actor_movies_cost: 0.020062, movie_similarity_cost: 0.0 },
      ];

      const graph = { type: "bar" as const };
      const result = transformDataForCompletionsGraph({ data, graph });

      expect(result[0]).toHaveProperty("x", "2025-09-03");
      expect(result[0]).toHaveProperty("actor_movies_cost", 0.6567310000000002);
      expect(result[0]).toHaveProperty("movie_similarity_cost", 0.0);
    });

    it("should handle single series data", () => {
      const data = [
        { category: "A", value: 100 },
        { category: "B", value: 200 },
      ];

      const graph = { type: "bar" as const };
      const result = transformDataForCompletionsGraph({ data, graph });

      expect(result[0]).toEqual({ x: "A", y: 100 });
      expect(result[1]).toEqual({ x: "B", y: 200 });
    });

    it("should handle multi-Y axis line charts", () => {
      const data = [
        { date: "2025-01-01", revenue: 1000, expenses: 500, profit: 500 },
        { date: "2025-01-02", revenue: 1200, expenses: 600, profit: 600 },
      ];

      const graph = {
        type: "line" as const,
        y: [{ field: "revenue" }, { field: "expenses" }, { field: "profit" }],
      };
      const result = transformDataForCompletionsGraph({ data, graph });

      expect(result[0]).toEqual({
        x: "2025-01-01",
        revenue: 1000,
        expenses: 500,
        profit: 500,
      });
    });

    it("should handle empty data", () => {
      const result = transformDataForCompletionsGraph({
        data: [],
        graph: { type: "bar" as const },
      });

      expect(result).toEqual([]);
    });

    it("should handle agent_id series transformation", () => {
      const data = [
        { agent_id: "actor-movies-experiment", date: "2025-09-03", total_cost: 0.6567310000000002 },
        { agent_id: "actor-movies-experiment", date: "2025-09-04", total_cost: 0.020062 },
        { agent_id: "new-politician-info-experiment", date: "2025-09-05", total_cost: 0.001438 },
        { agent_id: "movie-similarity-experiment", date: "2025-09-08", total_cost: 0.09738200000000001 },
      ];

      const graph = { type: "bar" as const, y: [{ field: "total_cost" }] };
      const result = transformDataForCompletionsGraph({ data, graph });

      // Should group by date (x-axis) and agent_id (series)
      expect(result.length).toBeGreaterThan(0);
      expect(result[0]).toHaveProperty("x");
      expect(result[0]).toHaveProperty("actor-movies-experiment");
    });
  });
});
