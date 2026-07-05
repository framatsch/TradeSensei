import { formatPriceLabel } from "@/lib/executionPriceLabel";

describe("formatPriceLabel", () => {
  it("renders adjusted and raw when values differ", () => {
    expect(formatPriceLabel("50", "500")).toBe("$50.00 (raw: $500.00)");
  });

  it("renders only one value when adjusted equals raw", () => {
    expect(formatPriceLabel("50", "50")).toBe("$50.00");
    expect(formatPriceLabel("50.0", "50.00")).toBe("$50.00");
  });
});
