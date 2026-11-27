import { describe, it, expect } from "vitest";
import { normalizeHints } from "../utils/hints";

describe("normalizeHints Utility", () => {
  it("normalizes Python engine dictionary hints to standard hint array", () => {
    const rawDict = {
      Goals: 28,
      Age: 25,
      League: "Premier League",
    };

    const result = normalizeHints(rawDict);
    expect(result).toHaveLength(3);
    expect(result).toEqual([
      { label: "Goals", value: 28, icon_key: "goals" },
      { label: "Age", value: 25, icon_key: "age" },
      { label: "League", value: "Premier League", icon_key: "league" },
    ]);
  });

  it("normalizes dictionary hints with multi-word and special keys", () => {
    const rawDict = {
      "Clean Sheets": 14,
      "UCL Goals": 6,
      Cards: 2,
    };

    const result = normalizeHints(rawDict);
    expect(result).toHaveLength(3);
    expect(result[0]).toEqual({
      label: "Clean Sheets",
      value: 14,
      icon_key: "clean_sheets",
    });
    expect(result[1]).toEqual({
      label: "UCL Goals",
      value: 6,
      icon_key: "ucl_goals",
    });
    expect(result[2]).toEqual({
      label: "Cards",
      value: 2,
      icon_key: "cards",
    });
  });

  it("passes through array hints safely preserving icon_key", () => {
    const rawArray = [
      { label: "Goals", value: 30, icon_key: "goals" },
      { label: "Assists", value: 12, icon_key: "assists" },
      { label: "Age", value: 23, icon_key: "age" },
    ];

    const result = normalizeHints(rawArray);
    expect(result).toEqual(rawArray);
  });

  it("handles null, undefined, and non-object inputs without throwing", () => {
    expect(normalizeHints(null)).toEqual([]);
    expect(normalizeHints(undefined)).toEqual([]);
    expect(normalizeHints({} as any)).toEqual([]);
    expect(normalizeHints("not an object" as any)).toEqual([]);
    expect(normalizeHints(123 as any)).toEqual([]);
  });

  it("handles arrays with missing labels or null items safely", () => {
    const mixed = [
      null,
      { label: "Goals", value: 10 },
      { label: "", value: "N/A" },
    ] as any;

    const result = normalizeHints(mixed);
    expect(result).toHaveLength(2);
    expect(result[0].label).toBe("Goals");
    expect(result[0].icon_key).toBe("goals");
    expect(result[1].label).toBe("");
    expect(result[1].icon_key).toBe("default");
  });
});
