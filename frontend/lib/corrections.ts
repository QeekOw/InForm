// Plausible physiological ranges and units for InBody fields.
// Enforces ADR-0008: fail-closed posture remains intact. A person can supply
// values for unread fields, or correct misread fields, but typed values are
// validated for plausible range and unit before acceptance so slipped decimals
// cannot produce nonsense plans.

export type FieldConstraint = {
  key: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  integer?: boolean;
};

export const FIELD_CONSTRAINTS: Record<string, FieldConstraint> = {
  weight_kg: {
    key: "weight_kg",
    label: "Weight",
    unit: "kg",
    min: 20,
    max: 300,
  },
  lean_body_mass_kg: {
    key: "lean_body_mass_kg",
    label: "Lean Body Mass",
    unit: "kg",
    min: 10,
    max: 250,
  },
  percent_body_fat: {
    key: "percent_body_fat",
    label: "Percent Body Fat",
    unit: "%",
    min: 3,
    max: 75,
  },
  skeletal_muscle_mass_kg: {
    key: "skeletal_muscle_mass_kg",
    label: "Skeletal Muscle Mass",
    unit: "kg",
    min: 5,
    max: 150,
  },
  basal_metabolic_rate_kcal: {
    key: "basal_metabolic_rate_kcal",
    label: "Basal Metabolic Rate",
    unit: "kcal",
    min: 500,
    max: 5000,
  },
  visceral_fat_level: {
    key: "visceral_fat_level",
    label: "Visceral Fat Level",
    unit: "level",
    min: 1,
    max: 30,
    integer: true,
  },
  "segmental_lean.left_arm_kg": {
    key: "segmental_lean.left_arm_kg",
    label: "Left Arm",
    unit: "kg",
    min: 0.5,
    max: 15,
  },
  "segmental_lean.right_arm_kg": {
    key: "segmental_lean.right_arm_kg",
    label: "Right Arm",
    unit: "kg",
    min: 0.5,
    max: 15,
  },
  "segmental_lean.left_leg_kg": {
    key: "segmental_lean.left_leg_kg",
    label: "Left Leg",
    unit: "kg",
    min: 1,
    max: 35,
  },
  "segmental_lean.right_leg_kg": {
    key: "segmental_lean.right_leg_kg",
    label: "Right Leg",
    unit: "kg",
    min: 1,
    max: 35,
  },
  "segmental_lean.trunk_kg": {
    key: "segmental_lean.trunk_kg",
    label: "Trunk",
    unit: "kg",
    min: 5,
    max: 100,
  },
};

/** Normalizes a short or dotted field key to standard dotted notation. */
export function normalizeFieldKey(key: string): string {
  if (
    [
      "left_arm_kg",
      "right_arm_kg",
      "left_leg_kg",
      "right_leg_kg",
      "trunk_kg",
    ].includes(key)
  ) {
    return `segmental_lean.${key}`;
  }
  return key;
}

/** Human-friendly label for any field key. */
export function getFieldLabel(key: string): string {
  const norm = normalizeFieldKey(key);
  return FIELD_CONSTRAINTS[norm]?.label ?? key;
}

/** Validates a field value for plausible range and integer requirements.
 * Returns an error string if invalid, or null if valid. */
export function validateFieldValue(
  key: string,
  value: number | null,
): string | null {
  if (value === null) return null;
  const norm = normalizeFieldKey(key);
  const constraint = FIELD_CONSTRAINTS[norm];
  if (!constraint) return null;

  if (constraint.integer && !Number.isInteger(value)) {
    return `${constraint.label} must be a whole number`;
  }

  if (value < constraint.min || value > constraint.max) {
    const unitSuffix = constraint.unit ? ` ${constraint.unit}` : "";
    return `${constraint.label} must be between ${constraint.min} and ${constraint.max}${unitSuffix}`;
  }

  return null;
}
