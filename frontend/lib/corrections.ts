// Plausible physiological ranges and units for InBody fields.
// Enforces ADR-0008: fail-closed posture remains intact. A person can supply
// values for unread fields, or correct misread fields, but typed values are
// validated for plausible range and unit before acceptance so slipped decimals
// or wrong units cannot produce nonsense plans.

export type FieldConstraint = {
  key: string;
  label: string;
  unit: string;
  allowedUnits: string[];
  min: number;
  max: number;
  integer?: boolean;
};

export const FIELD_CONSTRAINTS: Record<string, FieldConstraint> = {
  weight_kg: {
    key: "weight_kg",
    label: "Weight",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
    min: 20,
    max: 300,
  },
  lean_body_mass_kg: {
    key: "lean_body_mass_kg",
    label: "Lean Body Mass",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
    min: 10,
    max: 250,
  },
  percent_body_fat: {
    key: "percent_body_fat",
    label: "Percent Body Fat",
    unit: "%",
    allowedUnits: ["%", "percent", "pct"],
    min: 3,
    max: 75,
  },
  skeletal_muscle_mass_kg: {
    key: "skeletal_muscle_mass_kg",
    label: "Skeletal Muscle Mass",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
    min: 5,
    max: 150,
  },
  basal_metabolic_rate_kcal: {
    key: "basal_metabolic_rate_kcal",
    label: "Basal Metabolic Rate",
    unit: "kcal",
    allowedUnits: ["kcal", "cal", "calories", "kcal."],
    min: 500,
    max: 5000,
  },
  visceral_fat_level: {
    key: "visceral_fat_level",
    label: "Visceral Fat Level",
    unit: "level",
    allowedUnits: ["level", "lvl", ""],
    min: 1,
    max: 30,
    integer: true,
  },
  "segmental_lean.left_arm_kg": {
    key: "segmental_lean.left_arm_kg",
    label: "Left Arm",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
    min: 0.5,
    max: 15,
  },
  "segmental_lean.right_arm_kg": {
    key: "segmental_lean.right_arm_kg",
    label: "Right Arm",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
    min: 0.5,
    max: 15,
  },
  "segmental_lean.left_leg_kg": {
    key: "segmental_lean.left_leg_kg",
    label: "Left Leg",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
    min: 1,
    max: 35,
  },
  "segmental_lean.right_leg_kg": {
    key: "segmental_lean.right_leg_kg",
    label: "Right Leg",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
    min: 1,
    max: 35,
  },
  "segmental_lean.trunk_kg": {
    key: "segmental_lean.trunk_kg",
    label: "Trunk",
    unit: "kg",
    allowedUnits: ["kg", "kg."],
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

export type FieldValidationResult = {
  value: number | null;
  unit?: string;
  error: string | null;
};

/** Parses a human-typed input string (which may include a typed unit, e.g. "70 kg" or "150 lbs"),
 * and validates plausible range and unit before acceptance. */
export function parseAndValidateFieldInput(
  key: string,
  raw: string,
): FieldValidationResult {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { value: null, error: null };
  }

  const norm = normalizeFieldKey(key);
  const constraint = FIELD_CONSTRAINTS[norm];
  if (!constraint) {
    return { value: Number(trimmed), error: null };
  }

  // Matches numeric prefix followed by optional unit suffix
  const match = trimmed.match(/^([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z%]*)$/);
  if (!match) {
    return { value: null, error: `Please enter a valid number for ${constraint.label}` };
  }

  const num = Number(match[1]);
  const typedUnit = match[2] ? match[2].trim() : undefined;

  // Unit validation (rejection of wrong units)
  if (typedUnit) {
    const lowerUnit = typedUnit.toLowerCase();
    if (!constraint.allowedUnits.includes(lowerUnit)) {
      return {
        value: num,
        unit: typedUnit,
        error: `Invalid unit '${typedUnit}' for ${constraint.label} (expected '${constraint.unit}')`,
      };
    }
  }

  // Integer requirement
  if (constraint.integer && !Number.isInteger(num)) {
    return {
      value: num,
      unit: typedUnit ?? constraint.unit,
      error: `${constraint.label} must be a whole number`,
    };
  }

  // Range validation
  if (num < constraint.min || num > constraint.max) {
    const unitSuffix = constraint.unit ? ` ${constraint.unit}` : "";
    return {
      value: num,
      unit: typedUnit ?? constraint.unit,
      error: `${constraint.label} must be between ${constraint.min} and ${constraint.max}${unitSuffix}`,
    };
  }

  return {
    value: num,
    unit: typedUnit ?? constraint.unit,
    error: null,
  };
}

/** Validates an already-parsed field value and optional unit. */
export function validateFieldValue(
  key: string,
  value: number | null,
  unit?: string,
): string | null {
  if (value === null) return null;
  const norm = normalizeFieldKey(key);
  const constraint = FIELD_CONSTRAINTS[norm];
  if (!constraint) return null;

  if (unit) {
    const lowerUnit = unit.trim().toLowerCase();
    if (!constraint.allowedUnits.includes(lowerUnit)) {
      return `Invalid unit '${unit}' for ${constraint.label} (expected '${constraint.unit}')`;
    }
  }

  if (constraint.integer && !Number.isInteger(value)) {
    return `${constraint.label} must be a whole number`;
  }

  if (value < constraint.min || value > constraint.max) {
    const unitSuffix = constraint.unit ? ` ${constraint.unit}` : "";
    return `${constraint.label} must be between ${constraint.min} and ${constraint.max}${unitSuffix}`;
  }

  return null;
}

/**
 * Returns the list of flagged fields that have neither been corrected nor confirmed.
 *
 * Spec: "A flagged field blocks the plan until the person acts on it, either way."
 */
export function getUnresolvedFlagged(
  flagged?: string[] | Set<string> | null,
  corrected?: string[] | Set<string> | Record<string, unknown> | null,
  confirmed?: string[] | Set<string> | null,
): string[] {
  if (!flagged) return [];
  const flaggedArr = flagged instanceof Set ? Array.from(flagged) : flagged;
  if (flaggedArr.length === 0) return [];

  const correctedKeys = new Set<string>();
  if (corrected instanceof Set) {
    corrected.forEach((k) => correctedKeys.add(normalizeFieldKey(k)));
  } else if (Array.isArray(corrected)) {
    corrected.forEach((k) => correctedKeys.add(normalizeFieldKey(k)));
  } else if (corrected && typeof corrected === "object") {
    Object.keys(corrected).forEach((k) => correctedKeys.add(normalizeFieldKey(k)));
  }

  const confirmedSet = new Set<string>();
  if (confirmed instanceof Set) {
    confirmed.forEach((k) => confirmedSet.add(normalizeFieldKey(k)));
  } else if (Array.isArray(confirmed)) {
    confirmed.forEach((k) => confirmedSet.add(normalizeFieldKey(k)));
  }

  return flaggedArr
    .map(normalizeFieldKey)
    .filter((f) => !correctedKeys.has(f) && !confirmedSet.has(f));
}
