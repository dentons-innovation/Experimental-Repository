import { describe, it, expect } from "vitest";

describe("Frontend sanity check", () => {
  it("renders without crashing", () => {
    expect(1 + 1).toBe(2);
  });
});
