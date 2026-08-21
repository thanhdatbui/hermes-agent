import { describe, it, expect } from "vitest";
import {
  EFFORT_OPTIONS,
  effortOptionsForModel,
  isDeepSeekV4Model,
  VALID_EFFORTS,
  normalizeEffort,
} from "./reasoning-effort";

describe("normalizeEffort", () => {
  it("treats empty/unset as the Hermes default (medium)", () => {
    expect(normalizeEffort("")).toBe("medium");
    expect(normalizeEffort(null)).toBe("medium");
    expect(normalizeEffort(undefined)).toBe("medium");
    expect(normalizeEffort("   ")).toBe("medium");
  });

  it("passes through every valid effort level", () => {
    for (const level of ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]) {
      expect(normalizeEffort(level)).toBe(level);
    }
  });

  it("is case- and whitespace-insensitive", () => {
    expect(normalizeEffort("HIGH")).toBe("high");
    expect(normalizeEffort("  XHigh  ")).toBe("xhigh");
  });

  it("falls back to medium for unknown values", () => {
    expect(normalizeEffort("turbo")).toBe("medium");
    expect(normalizeEffort(42)).toBe("medium");
  });

  it("uses DeepSeek V4's native levels and default", () => {
    expect(normalizeEffort("", "cmc/deepseek/deepseek-v4-flash")).toBe("high");
    expect(normalizeEffort("medium", "deepseek/deepseek-v4-flash")).toBe("high");
    expect(normalizeEffort("max", "deepseek-v4-flash")).toBe("max");
    expect(normalizeEffort("none", "deepseek-v4-flash")).toBe("none");
  });
});

describe("EFFORT_OPTIONS", () => {
  it("every option value is in VALID_EFFORTS (no orphan labels)", () => {
    for (const opt of EFFORT_OPTIONS) {
      expect(VALID_EFFORTS.has(opt.value)).toBe(true);
    }
  });

  it("covers the real reasoning levels plus thinking-off", () => {
    // Invariant against hermes_constants.VALID_REASONING_EFFORTS + 'none'.
    const values = new Set(EFFORT_OPTIONS.map((o) => o.value));
    for (const level of ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]) {
      expect(values.has(level)).toBe(true);
    }
  });

  it("only exposes native DeepSeek V4 levels", () => {
    expect(isDeepSeekV4Model("cmc/deepseek/deepseek-v4-flash")).toBe(true);
    expect(isDeepSeekV4Model("nous/hermes-4")).toBe(false);
    expect(effortOptionsForModel("deepseek/deepseek-v4-flash").map((o) => o.value)).toEqual([
      "none",
      "low",
      "high",
      "max",
    ]);
  });
});
