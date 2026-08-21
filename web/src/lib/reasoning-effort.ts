/**
 * Pure reasoning-effort helpers shared by the dashboard ReasoningPicker.
 *
 * Kept DOM-free so the node-environment vitest harness can cover the
 * resolution logic without loading React or the UI kit.
 *
 * Values mirror hermes_constants.VALID_REASONING_EFFORTS plus `none`
 * (thinking-off). DeepSeek V4 has its own native subset: low/high/max.
 */

export interface EffortOption {
  value: string;
  label: string;
}

export const EFFORT_OPTIONS: ReadonlyArray<EffortOption> = [
  { value: "none", label: "Off (no thinking)" },
  { value: "minimal", label: "Minimal" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "xhigh", label: "Extra High" },
  { value: "max", label: "Max" },
  { value: "ultra", label: "Ultra" },
];

export const VALID_EFFORTS: ReadonlySet<string> = new Set(
  EFFORT_OPTIONS.map((o) => o.value),
);

export function isDeepSeekV4Model(model: string): boolean {
  const normalized = String(model ?? "").trim().toLowerCase();
  if (!normalized) return false;
  const modelId = normalized.split("/").pop()?.split(":")[0] ?? "";
  return modelId.startsWith("deepseek-v4-") || modelId === "worker" || modelId === "deepseek-v4";
}

export function effortOptionsForModel(
  model: string,
): ReadonlyArray<EffortOption> {
  if (!isDeepSeekV4Model(model)) return EFFORT_OPTIONS;
  return EFFORT_OPTIONS.filter(
    (option) => option.value === "none" || ["low", "high", "max"].includes(option.value),
  );
}

export function validEffortsForModel(model: string): ReadonlySet<string> {
  return new Set(effortOptionsForModel(model).map((option) => option.value));
}

export function defaultEffortForModel(model: string): string {
  return isDeepSeekV4Model(model) ? "high" : "medium";
}

/** Normalize a raw `agent.reasoning_effort` config value to a selectable
 *  option. Empty/unknown → the active model's native default. */
export function normalizeEffort(raw: unknown, model = ""): string {
  const value = String(raw ?? "").trim().toLowerCase();
  const valid = validEffortsForModel(model);
  if (!value) return defaultEffortForModel(model);
  if (value === "false" || value === "disabled") return "none";
  return valid.has(value) ? value : defaultEffortForModel(model);
}
