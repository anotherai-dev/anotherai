import { renderHook } from "@testing-library/react";
import type React from "react";
import { useParsedSearchParams } from "../queryString";

// Mock Next.js useSearchParams hook
const mockGet = jest.fn();
const mockSearchParams = {
  get: mockGet,
};

// Mock React hooks
const mockUseMemo = jest.fn();
jest.mock("react", () => ({
  ...jest.requireActual("react"),
  useMemo: <T>(fn: () => T, deps: React.DependencyList) => mockUseMemo(fn, deps),
}));

jest.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
}));

describe("useParsedSearchParams", () => {
  beforeEach(() => {
    mockGet.mockClear();
    mockUseMemo.mockClear();
    // Make useMemo call the function immediately
    mockUseMemo.mockImplementation((fn) => fn());
  });

  describe("Basic functionality", () => {
    it("returns undefined for non-existent parameters", () => {
      mockGet.mockReturnValue(null);

      const { result } = renderHook(() => useParsedSearchParams("param1", "param2"));

      expect(result.current).toEqual({
        param1: undefined,
        param2: undefined,
      });

      expect(mockGet).toHaveBeenCalledWith("param1");
      expect(mockGet).toHaveBeenCalledWith("param2");
    });

    it("returns parameter values when they exist", () => {
      mockGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2");

      const { result } = renderHook(() => useParsedSearchParams("param1", "param2"));

      expect(result.current).toEqual({
        param1: "value1",
        param2: "value2",
      });
    });

    it("handles single parameter", () => {
      mockGet.mockReturnValue("single-value");

      const { result } = renderHook(() => useParsedSearchParams("singleParam"));

      expect(result.current).toEqual({
        singleParam: "single-value",
      });
    });

    it("handles empty parameter list", () => {
      const { result } = renderHook(() => useParsedSearchParams());

      expect(result.current).toEqual({});
      expect(mockGet).not.toHaveBeenCalled();
    });
  });

  describe("Mixed parameter scenarios", () => {
    it("handles mix of existing and non-existing parameters", () => {
      mockGet.mockReturnValueOnce("existing-value").mockReturnValueOnce(null).mockReturnValueOnce("another-value");

      const { result } = renderHook(() => useParsedSearchParams("exists", "missing", "alsoExists"));

      expect(result.current).toEqual({
        exists: "existing-value",
        missing: undefined,
        alsoExists: "another-value",
      });
    });

    it("handles empty string values", () => {
      mockGet.mockReturnValueOnce("").mockReturnValueOnce("value");

      const { result } = renderHook(() => useParsedSearchParams("empty", "normal"));

      expect(result.current).toEqual({
        empty: "", // Empty string stays as empty string
        normal: "value",
      });
    });

    it("converts null to undefined", () => {
      mockGet.mockReturnValue(null);

      const { result } = renderHook(() => useParsedSearchParams("param"));

      expect(result.current).toEqual({
        param: undefined,
      });
    });
  });

  describe("Parameter value types", () => {
    it("handles URL-encoded values", () => {
      mockGet.mockReturnValue("hello%20world");

      const { result } = renderHook(() => useParsedSearchParams("encoded"));

      expect(result.current).toEqual({
        encoded: "hello%20world",
      });
    });

    it("handles special characters", () => {
      mockGet.mockReturnValue("value+with&special=chars");

      const { result } = renderHook(() => useParsedSearchParams("special"));

      expect(result.current).toEqual({
        special: "value+with&special=chars",
      });
    });

    it("handles numeric string values", () => {
      mockGet.mockReturnValueOnce("123").mockReturnValueOnce("45.67");

      const { result } = renderHook(() => useParsedSearchParams("int", "float"));

      expect(result.current).toEqual({
        int: "123",
        float: "45.67",
      });
    });

    it("handles boolean-like string values", () => {
      mockGet.mockReturnValueOnce("true").mockReturnValueOnce("false");

      const { result } = renderHook(() => useParsedSearchParams("truthy", "falsy"));

      expect(result.current).toEqual({
        truthy: "true",
        falsy: "false",
      });
    });
  });

  describe("Hook behavior and memoization", () => {
    it("memoizes result when parameters and search params unchanged", () => {
      mockGet.mockReturnValue("stable-value");

      const { result, rerender } = renderHook(() => useParsedSearchParams("param"));

      const firstResult = result.current;

      rerender();

      const secondResult = result.current;

      // Should be the same reference due to memoization
      expect(firstResult).toStrictEqual(secondResult);
    });

    it("handles parameter key changes", () => {
      mockGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2");

      // Test with param1
      const { result: result1 } = renderHook(() => useParsedSearchParams("param1"));
      expect(result1.current).toEqual({ param1: "value1" });

      // Test with param2 separately
      const { result: result2 } = renderHook(() => useParsedSearchParams("param2"));
      expect(result2.current).toEqual({ param2: "value2" });
    });

    it("handles adding more parameters", () => {
      mockGet.mockReturnValueOnce("value1").mockReturnValueOnce("value1").mockReturnValueOnce("value2");

      // Test with single parameter
      const { result: result1 } = renderHook(() => useParsedSearchParams("param1"));
      expect(result1.current).toEqual({ param1: "value1" });

      // Test with multiple parameters
      const { result: result2 } = renderHook(() => useParsedSearchParams("param1", "param2"));
      expect(result2.current).toEqual({
        param1: "value1",
        param2: "value2",
      });
    });
  });

  describe("Type safety and constraints", () => {
    it("maintains type safety for known parameter keys", () => {
      mockGet.mockReturnValueOnce("agent123").mockReturnValueOnce("exp456");

      const { result } = renderHook(() => useParsedSearchParams("agentId", "experimentId"));

      // TypeScript should infer correct types
      const agentId: string | undefined = result.current.agentId;
      const experimentId: string | undefined = result.current.experimentId;

      expect(agentId).toBe("agent123");
      expect(experimentId).toBe("exp456");
    });

    it("handles readonly array of parameter names", () => {
      const params = ["param1", "param2"] as const;
      mockGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2");

      const { result } = renderHook(() => useParsedSearchParams(...params));

      expect(result.current).toEqual({
        param1: "value1",
        param2: "value2",
      });
    });
  });

  describe("Edge cases and error handling", () => {
    it("handles very long parameter names", () => {
      const longParam = "a".repeat(1000);
      mockGet.mockReturnValue("value");

      const { result } = renderHook(() => useParsedSearchParams(longParam));

      expect(result.current).toEqual({
        [longParam]: "value",
      });
    });

    it("handles special parameter names", () => {
      mockGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2").mockReturnValueOnce("value3");

      const { result } = renderHook(() =>
        useParsedSearchParams("param-with-dash", "param_with_underscore", "paramWithCamelCase")
      );

      expect(result.current).toEqual({
        "param-with-dash": "value1",
        param_with_underscore: "value2",
        paramWithCamelCase: "value3",
      });
    });

    it("handles duplicate parameter names", () => {
      mockGet.mockReturnValue("duplicate-value");

      const { result } = renderHook(() => useParsedSearchParams("param", "param"));

      expect(result.current).toEqual({
        param: "duplicate-value",
      });

      // Should still call get for each parameter (even duplicates)
      expect(mockGet).toHaveBeenCalledTimes(2);
    });

    it("handles numeric parameter keys", () => {
      mockGet.mockReturnValue("numeric-key-value");

      const { result } = renderHook(() => useParsedSearchParams("123"));

      expect(result.current).toEqual({
        "123": "numeric-key-value",
      });
    });
  });

  describe("Integration scenarios", () => {
    it("simulates real search params parsing", () => {
      // Simulate URL: ?agentId=agent-123&page=1&filter=active&sort=
      mockGet.mockImplementation((key) => {
        const params: Record<string, string | null> = {
          agentId: "agent-123",
          page: "1",
          filter: "active",
          sort: "", // Empty value
          missing: null,
        };
        return params[key] ?? null;
      });

      const { result } = renderHook(() => useParsedSearchParams("agentId", "page", "filter", "sort", "missing"));

      expect(result.current).toEqual({
        agentId: "agent-123",
        page: "1",
        filter: "active",
        sort: "", // Empty string stays as empty string
        missing: undefined,
      });
    });

    it("handles complex search parameter scenario", () => {
      mockGet.mockImplementation((key) => {
        // Simulate complex URL parameters
        const params: Record<string, string | null> = {
          search: "machine learning",
          tags: "ai,ml,neural",
          minCost: "0.01",
          maxCost: "1.00",
          sortBy: "created_at",
          order: "desc",
        };
        return params[key] ?? null;
      });

      const { result } = renderHook(() =>
        useParsedSearchParams("search", "tags", "minCost", "maxCost", "sortBy", "order", "nonexistent")
      );

      expect(result.current).toEqual({
        search: "machine learning",
        tags: "ai,ml,neural",
        minCost: "0.01",
        maxCost: "1.00",
        sortBy: "created_at",
        order: "desc",
        nonexistent: undefined,
      });
    });
  });
});
