import { formatValueWithUnit } from "../utils";

describe("formatValueWithUnit", () => {
  it("should format values with currency symbols as prefixes", () => {
    expect(formatValueWithUnit("1.23", "$")).toBe("$1.23");
    expect(formatValueWithUnit("100", "€")).toBe("€100");
    expect(formatValueWithUnit("50", "£")).toBe("£50");
    expect(formatValueWithUnit("1000", "USD")).toBe("USD1000");
  });

  it("should format values with non-currency units as suffixes", () => {
    expect(formatValueWithUnit("5", "runs")).toBe("5 runs");
    expect(formatValueWithUnit("10", "tokens")).toBe("10 tokens");
    expect(formatValueWithUnit("2.5", "seconds")).toBe("2.5 seconds");
  });

  it("should handle undefined units", () => {
    expect(formatValueWithUnit("42", undefined)).toBe("42");
  });

  it("should handle empty string units", () => {
    expect(formatValueWithUnit("42", "")).toBe("42");
  });
});
