import { DEFAULT_CHART_COLORS, SeriesConfig, autoDetectSeries } from "../utils";

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
});
