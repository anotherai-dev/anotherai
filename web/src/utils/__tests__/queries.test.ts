import { buildQuery, defaultQuery, defaultQueryParts } from "../queries";

describe("Query Building Utilities", () => {
  describe("defaultQueryParts", () => {
    it("contains expected query parts", () => {
      expect(defaultQueryParts).toHaveProperty("select");
      expect(defaultQueryParts).toHaveProperty("from");
      expect(defaultQueryParts).toHaveProperty("orderBy");
      expect(defaultQueryParts).toHaveProperty("limit");
    });

    it("has correct SELECT clause with expected columns", () => {
      const expectedColumns = [
        "id",
        "agent_id",
        "input_messages",
        "input_variables",
        "output_messages",
        "output_error",
        "version",
        "duration_ds",
        "cost_usd",
        "created_at",
      ];

      expectedColumns.forEach((column) => {
        expect(defaultQueryParts.select).toContain(column);
      });

      expect(defaultQueryParts.select.startsWith("SELECT")).toBe(true);
    });

    it("has correct FROM clause", () => {
      expect(defaultQueryParts.from).toBe("FROM completions");
    });

    it("has correct ORDER BY clause", () => {
      expect(defaultQueryParts.orderBy).toBe("ORDER BY created_at DESC");
    });

    it("has correct LIMIT clause", () => {
      expect(defaultQueryParts.limit).toBe("LIMIT 100");
    });

    it("contains valid SQL syntax", () => {
      Object.values(defaultQueryParts).forEach((part) => {
        expect(typeof part).toBe("string");
        expect(part.trim()).toBe(part); // No leading/trailing whitespace
        expect(part.length).toBeGreaterThan(0);
      });
    });
  });

  describe("buildQuery", () => {
    it("builds query without WHERE clause when no whereClause provided", () => {
      const result = buildQuery();

      expect(result).toContain(defaultQueryParts.select);
      expect(result).toContain(defaultQueryParts.from);
      expect(result).toContain(defaultQueryParts.orderBy);
      expect(result).toContain(defaultQueryParts.limit);
      expect(result).not.toContain("WHERE");
    });

    it("builds query with WHERE clause when whereClause provided", () => {
      const whereClause = "agent_id = 'test-agent'";
      const result = buildQuery(whereClause);

      expect(result).toContain(defaultQueryParts.select);
      expect(result).toContain(defaultQueryParts.from);
      expect(result).toContain(`WHERE ${whereClause}`);
      expect(result).toContain(defaultQueryParts.orderBy);
      expect(result).toContain(defaultQueryParts.limit);
    });

    it("handles empty string whereClause", () => {
      const result = buildQuery("");

      expect(result).not.toContain("WHERE");
      expect(result).toContain(defaultQueryParts.select);
      expect(result).toContain(defaultQueryParts.from);
    });

    it("handles null whereClause", () => {
      const result = buildQuery(null);

      expect(result).not.toContain("WHERE");
      expect(result).toContain(defaultQueryParts.select);
    });

    it("handles undefined whereClause", () => {
      const result = buildQuery(undefined);

      expect(result).not.toContain("WHERE");
      expect(result).toContain(defaultQueryParts.select);
    });

    it("joins query parts with spaces", () => {
      const whereClause = "cost_usd > 0.01";
      const result = buildQuery(whereClause);

      // Should not have double spaces
      expect(result).not.toMatch(/  +/);

      // Should be properly spaced
      const parts = result.split(" ");
      expect(parts.length).toBeGreaterThan(5);
    });

    it("maintains correct SQL order", () => {
      const whereClause = "agent_id = 'test' AND cost_usd > 0";
      const result = buildQuery(whereClause);

      const selectIndex = result.indexOf("SELECT");
      const fromIndex = result.indexOf("FROM");
      const whereIndex = result.indexOf("WHERE");
      const orderIndex = result.indexOf("ORDER BY");
      const limitIndex = result.indexOf("LIMIT");

      expect(selectIndex).toBeLessThan(fromIndex);
      expect(fromIndex).toBeLessThan(whereIndex);
      expect(whereIndex).toBeLessThan(orderIndex);
      expect(orderIndex).toBeLessThan(limitIndex);
    });

    it("handles complex WHERE clauses", () => {
      const complexWhere =
        "agent_id IN ('agent1', 'agent2') AND created_at >= '2023-01-01' AND (cost_usd > 0.1 OR duration_ds > 1000)";
      const result = buildQuery(complexWhere);

      expect(result).toContain(`WHERE ${complexWhere}`);
      expect(result).toContain("SELECT");
      expect(result).toContain("FROM completions");
    });

    it("produces valid-looking SQL", () => {
      const result = buildQuery("agent_id = 'test'");

      // Should start with SELECT
      expect(result).toMatch(/^SELECT\s+/);

      // Should contain FROM
      expect(result).toMatch(/\s+FROM\s+completions\s+/);

      // Should contain WHERE
      expect(result).toMatch(/\s+WHERE\s+/);

      // Should end with LIMIT
      expect(result).toMatch(/\s+LIMIT\s+100$/);
    });
  });

  describe("defaultQuery", () => {
    it("is built using buildQuery without whereClause", () => {
      const expectedQuery = buildQuery();
      expect(defaultQuery).toBe(expectedQuery);
    });

    it("contains all default parts", () => {
      expect(defaultQuery).toContain(defaultQueryParts.select);
      expect(defaultQuery).toContain(defaultQueryParts.from);
      expect(defaultQuery).toContain(defaultQueryParts.orderBy);
      expect(defaultQuery).toContain(defaultQueryParts.limit);
    });

    it("does not contain WHERE clause", () => {
      expect(defaultQuery).not.toContain("WHERE");
    });

    it("is a valid SQL query structure", () => {
      // Should be a single line query
      expect(defaultQuery.split("\n")).toHaveLength(1);

      // Should contain expected SQL keywords in order
      const keywords = ["SELECT", "FROM", "ORDER BY", "LIMIT"];
      let lastIndex = -1;

      keywords.forEach((keyword) => {
        const index = defaultQuery.indexOf(keyword);
        expect(index).toBeGreaterThan(lastIndex);
        lastIndex = index;
      });
    });
  });

  describe("Query structure validation", () => {
    it("buildQuery produces consistent results", () => {
      const whereClause = "test_condition = 'value'";
      const result1 = buildQuery(whereClause);
      const result2 = buildQuery(whereClause);

      expect(result1).toBe(result2);
    });

    it("different WHERE clauses produce different results", () => {
      const where1 = "agent_id = 'test1'";
      const where2 = "agent_id = 'test2'";

      const result1 = buildQuery(where1);
      const result2 = buildQuery(where2);

      expect(result1).not.toBe(result2);
      expect(result1).toContain(where1);
      expect(result2).toContain(where2);
    });

    it("handles special characters in WHERE clause", () => {
      const whereClause = 'input_variables LIKE \'%"special":"value%\'';
      const result = buildQuery(whereClause);

      expect(result).toContain(whereClause);
    });

    it("preserves WHERE clause exactly as provided", () => {
      const originalWhere = "  agent_id = 'test'  AND  cost > 0  ";
      const result = buildQuery(originalWhere);

      expect(result).toContain(`WHERE ${originalWhere}`);
    });
  });

  describe("Performance and edge cases", () => {
    it("handles very long WHERE clauses", () => {
      const longConditions = Array(50)
        .fill(0)
        .map((_, i) => `field${i} = 'value${i}'`)
        .join(" AND ");
      const result = buildQuery(longConditions);

      expect(result).toContain(longConditions);
      expect(result.length).toBeGreaterThan(1000);
    });

    it("handles WHERE clause with line breaks", () => {
      const whereWithBreaks = "agent_id = 'test'\nAND cost_usd > 0";
      const result = buildQuery(whereWithBreaks);

      expect(result).toContain(whereWithBreaks);
    });

    it("buildQuery is pure function", () => {
      const original = { ...defaultQueryParts };

      buildQuery("test = 'value'");

      // Should not modify original defaultQueryParts
      expect(defaultQueryParts).toEqual(original);
    });

    it("handles boolean-like WHERE clauses", () => {
      const result1 = buildQuery("true");
      const result2 = buildQuery("false");
      const result3 = buildQuery("1 = 1");

      expect(result1).toContain("WHERE true");
      expect(result2).toContain("WHERE false");
      expect(result3).toContain("WHERE 1 = 1");
    });
  });

  describe("SQL injection prevention awareness", () => {
    it("does not sanitize WHERE clause (raw SQL building)", () => {
      // This test documents that the function doesn't sanitize input
      // This is expected behavior for a query builder, but callers should be aware
      const potentiallyDangerous = "1 = 1; DROP TABLE completions; --";
      const result = buildQuery(potentiallyDangerous);

      expect(result).toContain(potentiallyDangerous);
      // Note: This behavior means callers must sanitize inputs themselves
    });

    it("preserves single quotes in WHERE clause", () => {
      const whereWithQuotes = "name = 'O''Brien' AND title = 'Senior ''Developer'''";
      const result = buildQuery(whereWithQuotes);

      expect(result).toContain(whereWithQuotes);
    });
  });
});
