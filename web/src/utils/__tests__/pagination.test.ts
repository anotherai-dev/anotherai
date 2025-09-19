import {
  detectPaginationVariables,
  extractLimitFromQuery,
  replacePaginationVariables,
  calculatePaginationParams,
  processPaginationQuery,
} from "../pagination";

describe("Pagination Utilities", () => {
  describe("detectPaginationVariables", () => {
    it("detects pagination variables in query", () => {
      const query = "SELECT * FROM completions LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      expect(detectPaginationVariables(query)).toBe(true);
    });

    it("returns false when only limit variable is present", () => {
      const query = "SELECT * FROM completions LIMIT {limit:UInt32}";
      expect(detectPaginationVariables(query)).toBe(false);
    });

    it("returns false when only offset variable is present", () => {
      const query = "SELECT * FROM completions OFFSET {offset:UInt32}";
      expect(detectPaginationVariables(query)).toBe(false);
    });

    it("returns false when no pagination variables are present", () => {
      const query = "SELECT * FROM completions LIMIT 20 OFFSET 0";
      expect(detectPaginationVariables(query)).toBe(false);
    });

    it("is case insensitive", () => {
      const query = "SELECT * FROM completions LIMIT {LIMIT:UINT32} OFFSET {OFFSET:UINT32}";
      expect(detectPaginationVariables(query)).toBe(true);
    });

    it("handles mixed case variables", () => {
      const query = "SELECT * FROM completions LIMIT {Limit:UInt32} OFFSET {Offset:UInt32}";
      expect(detectPaginationVariables(query)).toBe(true);
    });
  });

  describe("extractLimitFromQuery", () => {
    it("extracts limit from pagination variable query", () => {
      const query = "SELECT * FROM completions LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      expect(extractLimitFromQuery(query)).toBe(20); // Default page size
    });

    it("extracts limit from regular LIMIT clause", () => {
      const query = "SELECT * FROM completions LIMIT 50 OFFSET 10";
      expect(extractLimitFromQuery(query)).toBe(50);
    });

    it("returns null when no LIMIT clause is found", () => {
      const query = "SELECT * FROM completions WHERE id = 'test'";
      expect(extractLimitFromQuery(query)).toBe(null);
    });

    it("handles multiple digit limits", () => {
      const query = "SELECT * FROM completions LIMIT 100";
      expect(extractLimitFromQuery(query)).toBe(100);
    });

    it("is case insensitive for LIMIT keyword", () => {
      const query = "SELECT * FROM completions limit 25";
      expect(extractLimitFromQuery(query)).toBe(25);
    });
  });

  describe("replacePaginationVariables", () => {
    it("replaces both limit and offset variables", () => {
      const query = "SELECT * FROM completions LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      const params = { limit: 25, offset: 50 };
      const result = replacePaginationVariables(query, params);
      
      expect(result).toBe("SELECT * FROM completions LIMIT 25 OFFSET 50");
    });

    it("handles multiple occurrences of variables", () => {
      const query = "SELECT *, {limit:UInt32} as page_size FROM completions LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      const params = { limit: 10, offset: 20 };
      const result = replacePaginationVariables(query, params);
      
      expect(result).toBe("SELECT *, 10 as page_size FROM completions LIMIT 10 OFFSET 20");
    });

    it("is case insensitive", () => {
      const query = "SELECT * FROM completions LIMIT {LIMIT:UINT32} OFFSET {OFFSET:UINT32}";
      const params = { limit: 15, offset: 30 };
      const result = replacePaginationVariables(query, params);
      
      expect(result).toBe("SELECT * FROM completions LIMIT 15 OFFSET 30");
    });

    it("handles zero values", () => {
      const query = "SELECT * FROM completions LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      const params = { limit: 0, offset: 0 };
      const result = replacePaginationVariables(query, params);
      
      expect(result).toBe("SELECT * FROM completions LIMIT 0 OFFSET 0");
    });

    it("leaves query unchanged when no variables present", () => {
      const query = "SELECT * FROM completions LIMIT 20 OFFSET 0";
      const params = { limit: 25, offset: 50 };
      const result = replacePaginationVariables(query, params);
      
      expect(result).toBe(query);
    });
  });

  describe("calculatePaginationParams", () => {
    it("calculates correct params for first page", () => {
      const result = calculatePaginationParams(1, 20);
      expect(result).toEqual({ limit: 20, offset: 0 });
    });

    it("calculates correct params for second page", () => {
      const result = calculatePaginationParams(2, 20);
      expect(result).toEqual({ limit: 20, offset: 20 });
    });

    it("calculates correct params for third page", () => {
      const result = calculatePaginationParams(3, 20);
      expect(result).toEqual({ limit: 20, offset: 40 });
    });

    it("handles different page sizes", () => {
      const result = calculatePaginationParams(2, 15);
      expect(result).toEqual({ limit: 15, offset: 15 });
    });

    it("handles page size of 1", () => {
      const result = calculatePaginationParams(5, 1);
      expect(result).toEqual({ limit: 1, offset: 4 });
    });

    it("handles large page numbers", () => {
      const result = calculatePaginationParams(100, 10);
      expect(result).toEqual({ limit: 10, offset: 990 });
    });
  });

  describe("processPaginationQuery", () => {
    it("processes query with pagination variables", () => {
      const query = "SELECT * FROM completions LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      const result = processPaginationQuery(query, 2, 15);
      
      expect(result.processedQuery).toBe("SELECT * FROM completions LIMIT 15 OFFSET 15");
      expect(result.hasPagination).toBe(true);
      expect(result.paginationInfo).toEqual({
        hasPagination: true,
        pageSize: 15,
        currentPage: 2,
      });
    });

    it("handles query without pagination variables", () => {
      const query = "SELECT * FROM completions LIMIT 20 OFFSET 0";
      const result = processPaginationQuery(query, 2, 15);
      
      expect(result.processedQuery).toBe(query);
      expect(result.hasPagination).toBe(false);
      expect(result.paginationInfo).toEqual({
        hasPagination: false,
        pageSize: 0,
        currentPage: 1,
      });
    });

    it("uses default values when not provided", () => {
      const query = "SELECT * FROM completions LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      const result = processPaginationQuery(query);
      
      expect(result.processedQuery).toBe("SELECT * FROM completions LIMIT 20 OFFSET 0");
      expect(result.hasPagination).toBe(true);
      expect(result.paginationInfo).toEqual({
        hasPagination: true,
        pageSize: 20,
        currentPage: 1,
      });
    });

    it("uses provided page size when pagination variables are detected", () => {
      const query = "SELECT * FROM completions WHERE id > 100 LIMIT {limit:UInt32} OFFSET {offset:UInt32}";
      const result = processPaginationQuery(query, 1, 25);
      
      // Should use provided page size when pagination variables are detected
      expect(result.paginationInfo.pageSize).toBe(25);
    });

    it("handles complex queries with multiple clauses", () => {
      const query = `
        SELECT id, agent_id, created_at 
        FROM completions 
        WHERE agent_id = 'test-agent' 
          AND created_at > '2023-01-01' 
        ORDER BY created_at DESC 
        LIMIT {limit:UInt32} 
        OFFSET {offset:UInt32}
      `;
      const result = processPaginationQuery(query, 3, 10);
      
      expect(result.hasPagination).toBe(true);
      expect(result.processedQuery).toContain("LIMIT 10");
      expect(result.processedQuery).toContain("OFFSET 20");
      expect(result.paginationInfo.currentPage).toBe(3);
      expect(result.paginationInfo.pageSize).toBe(10);
    });
  });
});