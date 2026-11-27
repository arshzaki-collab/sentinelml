import { CandidateHint } from "../types/game";

/**
 * Normalizes candidate statistical hints from any backend shape into a uniform array of CandidateHint.
 * Supports:
 * - Dict / Record shape from backend: { "Goals": 25, "Age": 24, "League": "Premier League" }
 * - Array shape: [ { label: "Goals", value: 25, icon_key: "goals" }, ... ]
 * - Missing or malformed data: returns [] without crashing
 */
export function normalizeHints(
  hints: Record<string, string | number> | CandidateHint[] | null | undefined
): CandidateHint[] {
  if (!hints) return [];

  // If already an array, ensure all required fields are present
  if (Array.isArray(hints)) {
    return hints
      .filter((h) => h != null)
      .map((h) => ({
        label: String(h.label ?? ""),
        value: h.value ?? "",
        icon_key:
          h.icon_key ||
          (h.label ? String(h.label).toLowerCase().replace(/[\s_]+/g, "_") : "default"),
      }));
  }

  // If dictionary / object from backend Python engine
  if (typeof hints === "object") {
    return Object.entries(hints).map(([label, value]) => ({
      label,
      value: value ?? "",
      icon_key: label.toLowerCase().replace(/[\s_]+/g, "_"),
    }));
  }

  return [];
}
