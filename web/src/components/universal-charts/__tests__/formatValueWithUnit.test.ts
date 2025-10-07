import { formatNumber, formatValueWithUnit } from "../utils";

describe("formatNumber", () => {
  it("should format large numbers with suffixes", () => {
    expect(formatNumber(2634982.83)).toBe("2.63m");
    expect(formatNumber(1234567)).toBe("1.23m");
    expect(formatNumber(5432)).toBe("5.43k");
    expect(formatNumber(1000)).toBe("1k");
    expect(formatNumber(999)).toBe("999");
  });

  it("should format regular numbers to 2 decimal places", () => {
    expect(formatNumber(2.6349823834589345698)).toBe("2.63");
    expect(formatNumber(12.345678)).toBe("12.35");
    expect(formatNumber(100)).toBe("100");
    expect(formatNumber(1.0)).toBe("1");
  });

  it("should handle small decimal numbers", () => {
    expect(formatNumber(0.123456)).toBe("0.1235");
    expect(formatNumber(0.1)).toBe("0.1");
    expect(formatNumber(0.9999)).toBe("0.9999");
  });

  it("should handle very small numbers", () => {
    expect(formatNumber(0.0000000004)).toBe("4.0e-10");
    expect(formatNumber(0.00000034234242342342)).toBe("3e-7");
    expect(formatNumber(0.000001)).toBe("0.000001");
  });

  it("should handle zero and negative numbers", () => {
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(-2.635)).toBe("-2.63");
    expect(formatNumber(-5432)).toBe("-5.43k");
  });

  it("should use scientific notation for extremely small numbers", () => {
    expect(formatNumber(0.0000000001)).toBe("1.0e-10");
  });
});

describe("formatValueWithUnit", () => {
  it("should format values with currency symbols as prefixes", () => {
    expect(formatValueWithUnit("1.23", "$")).toBe("$1.23");
    expect(formatValueWithUnit("1234567", "$")).toBe("$1.23m");
    expect(formatValueWithUnit("5432", "€")).toBe("€5.43k");
    expect(formatValueWithUnit("1000", "USD")).toBe("USD1k");
  });

  it("should format values with time units without spaces", () => {
    expect(formatValueWithUnit("1.5", "s")).toBe("1.5s");
    expect(formatValueWithUnit("2.6349823834589345698", "s")).toBe("2.63s");
  });

  it("should format values with count units with spaces", () => {
    expect(formatValueWithUnit("5", "count")).toBe("5 count");
    expect(formatValueWithUnit("1234", "completions")).toBe("1.23k completions");
    expect(formatValueWithUnit("2.5", "tokens")).toBe("2.5 tokens");
  });

  it("should handle intelligent number formatting", () => {
    expect(formatValueWithUnit("2.6349823834589345698", "$")).toBe("$2.63");
    expect(formatValueWithUnit("1234567", "count")).toBe("1.23m count");
    expect(formatValueWithUnit("0.00000034234242342342", "s")).toBe("3e-7s");
  });

  it("should handle undefined units", () => {
    expect(formatValueWithUnit("42", undefined)).toBe("42");
    expect(formatValueWithUnit("2.6349823834589345698", undefined)).toBe("2.63");
  });

  it("should handle empty string units", () => {
    expect(formatValueWithUnit("42", "")).toBe("42");
  });

  it("should handle non-numeric values as fallback", () => {
    expect(formatValueWithUnit("invalid", "$")).toBe("$invalid");
    expect(formatValueWithUnit("N/A", "count")).toBe("N/A count");
  });
});
