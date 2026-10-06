import { expect, it } from "vitest";
import {
  getUnresolvedFlagged,
  parseAndValidateFieldInput,
  updateFieldCorrection,
} from "./corrections";

it("records only changed values, including when retyping or reverting the original", () => {
  for (const [key, original, changed, raw] of [
    ["weight_kg", 70, 71, "70.0 kg"],
    ["left_arm_kg", 2.8, 2.9, "2.80 kg"],
    ["basal_metabolic_rate_kcal", 1500, 1600, "1500 kcal"],
  ] as const) {
    const parsed = parseAndValidateFieldInput(key, raw);
    expect(parsed.error).toBeNull();
    expect(updateFieldCorrection({}, key, parsed.value, original, parsed.unit)).toEqual({});

    const edited = updateFieldCorrection({}, key, changed, original, parsed.unit);
    expect(Object.values(edited)).toEqual([{ value: changed, unit: parsed.unit }]);
    expect(getUnresolvedFlagged([key], edited)).toEqual([]);

    const reverted = updateFieldCorrection(edited, key, parsed.value, original, parsed.unit);
    expect(reverted).toEqual({});
    expect(getUnresolvedFlagged([key], reverted)).toHaveLength(1);
    expect(getUnresolvedFlagged([key], reverted, [key])).toEqual([]);
  }

  expect(updateFieldCorrection({}, "weight_kg", 70, null, "kg"))
    .toEqual({ weight_kg: { value: 70, unit: "kg" } });
  expect(updateFieldCorrection({ left_arm_kg: { value: 2.9 } }, "left_arm_kg", 2.8, 2.8))
    .toEqual({});
  expect(updateFieldCorrection({ weight_kg: { value: 71 } }, "weight_kg", null, 70))
    .toEqual({});
});
