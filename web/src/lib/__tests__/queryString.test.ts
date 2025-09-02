import { renderHook } from "@testing-library/react";
import { useParsedSearchParams } from "../queryString";

// Access the global mock
declare global {
  var mockSearchParamsGet: jest.MockedFunction<any>;
}

describe("useParsedSearchParams", () => {
  beforeEach(() => {
    global.mockSearchParamsGet.mockClear();
  });

  describe("Basic functionality", () => {
    it("returns undefined for non-existent parameters", () => {
      global.mockSearchParamsGet.mockReturnValue(null);

      const { result } = renderHook(() => useParsedSearchParams("param1", "param2"));

      expect(result.current).toEqual({
        param1: undefined,
        param2: undefined,
      });

      expect(global.mockSearchParamsGet).toHaveBeenCalledWith("param1");
      expect(global.mockSearchParamsGet).toHaveBeenCalledWith("param2");
    });

    it("returns parameter values when they exist", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2");

      const { result } = renderHook(() => useParsedSearchParams("param1", "param2"));

      expect(result.current).toEqual({
        param1: "value1",
        param2: "value2",
      });
    });

    it("handles single parameter", () => {
      global.mockSearchParamsGet.mockReturnValue("single-value");

      const { result } = renderHook(() => useParsedSearchParams("singleParam"));

      expect(result.current).toEqual({
        singleParam: "single-value",
      });
    });

    it("handles empty parameter list", () => {
      const { result } = renderHook(() => useParsedSearchParams());

      expect(result.current).toEqual({});
      expect(global.mockSearchParamsGet).not.toHaveBeenCalled();
    });
  });

  describe("Mixed parameter scenarios", () => {
    it("handles mix of existing and non-existing parameters", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("existing-value").mockReturnValueOnce(null).mockReturnValueOnce("another-value");

      const { result } = renderHook(() => useParsedSearchParams("exists", "missing", "alsoExists"));

      expect(result.current).toEqual({
        exists: "existing-value",
        missing: undefined,
        alsoExists: "another-value",
      });
    });

    it("handles empty string values", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("").mockReturnValueOnce("value");

      const { result } = renderHook(() => useParsedSearchParams("empty", "normal"));

      expect(result.current).toEqual({
        empty: "", // Empty string stays as empty string
        normal: "value",
      });
    });

    it("converts null to undefined", () => {
      global.mockSearchParamsGet.mockReturnValue(null);

      const { result } = renderHook(() => useParsedSearchParams("param"));

      expect(result.current).toEqual({
        param: undefined,
      });
    });
  });

  describe("Parameter value types", () => {
    it("handles URL-encoded values", () => {
      global.mockSearchParamsGet.mockReturnValue("hello%20world");

      const { result } = renderHook(() => useParsedSearchParams("encoded"));

      expect(result.current).toEqual({
        encoded: "hello%20world",
      });
    });

    it("handles special characters", () => {
      global.mockSearchParamsGet.mockReturnValue("value+with&special=chars");

      const { result } = renderHook(() => useParsedSearchParams("special"));

      expect(result.current).toEqual({
        special: "value+with&special=chars",
      });
    });

    it("handles numeric string values", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("123").mockReturnValueOnce("45.67");

      const { result } = renderHook(() => useParsedSearchParams("int", "float"));

      expect(result.current).toEqual({
        int: "123",
        float: "45.67",
      });
    });

    it("handles boolean-like string values", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("true").mockReturnValueOnce("false");

      const { result } = renderHook(() => useParsedSearchParams("truthy", "falsy"));

      expect(result.current).toEqual({
        truthy: "true",
        falsy: "false",
      });
    });
  });

  describe("Hook behavior and memoization", () => {
    it("memoizes result when parameters and search params unchanged", () => {
      global.mockSearchParamsGet.mockReturnValue("stable-value");

      const { result, rerender } = renderHook(() => useParsedSearchParams("param"));

      const firstResult = result.current;

      rerender();

      const secondResult = result.current;

      // Should be the same reference due to memoization
      expect(firstResult).toStrictEqual(secondResult);
    });

    it("handles parameter key changes", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2");

      const { result, rerender } = renderHook(({ keys }) => useParsedSearchParams(...keys), {
        initialProps: { keys: ["param1"] as const },
      });

      expect(result.current).toEqual({ param1: "value1" });

      rerender({ keys: ["param2"] as const });

      expect(result.current).toEqual({ param2: "value2" });
    });

    it("handles adding more parameters", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("value1").mockReturnValueOnce("value1").mockReturnValueOnce("value2");

      const { result, rerender } = renderHook(({ keys }) => useParsedSearchParams(...keys), {
        initialProps: { keys: ["param1"] as const },
      });

      expect(result.current).toEqual({ param1: "value1" });

      rerender({ keys: ["param1", "param2"] as const });

      expect(result.current).toEqual({
        param1: "value1",
        param2: "value2",
      });
    });
  });

  describe("Type safety and constraints", () => {
    it("maintains type safety for known parameter keys", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("agent123").mockReturnValueOnce("exp456");

      const { result } = renderHook(() => useParsedSearchParams("agentId", "experimentId"));

      // TypeScript should infer correct types
      const agentId: string | undefined = result.current.agentId;
      const experimentId: string | undefined = result.current.experimentId;

      expect(agentId).toBe("agent123");
      expect(experimentId).toBe("exp456");
    });

    it("handles readonly array of parameter names", () => {
      const params = ["param1", "param2"] as const;
      global.mockSearchParamsGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2");

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
      global.mockSearchParamsGet.mockReturnValue("value");

      const { result } = renderHook(() => useParsedSearchParams(longParam));

      expect(result.current).toEqual({
        [longParam]: "value",
      });
    });

    it("handles special parameter names", () => {
      global.mockSearchParamsGet.mockReturnValueOnce("value1").mockReturnValueOnce("value2").mockReturnValueOnce("value3");

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
      global.mockSearchParamsGet.mockReturnValue("duplicate-value");

      const { result } = renderHook(() => useParsedSearchParams("param", "param"));

      expect(result.current).toEqual({
        param: "duplicate-value",
      });

      // Should still call get for each parameter (even duplicates)
      expect(global.mockSearchParamsGet).toHaveBeenCalledTimes(2);
    });

    it("handles numeric parameter keys", () => {
      global.mockSearchParamsGet.mockReturnValue("numeric-key-value");

      const { result } = renderHook(() => useParsedSearchParams("123"));

      expect(result.current).toEqual({
        "123": "numeric-key-value",
      });
    });
  });

  describe("Integration scenarios", () => {
    it("simulates real search params parsing", () => {
      // Simulate URL: ?agentId=agent-123&page=1&filter=active&sort=
      global.mockSearchParamsGet.mockImplementation((key) => {
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
      global.mockSearchParamsGet.mockImplementation((key) => {
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
