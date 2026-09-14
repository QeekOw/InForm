// Mirrors inform.inbody.InBodyPayload / inform.user.UserProfile (src/inform)
// so the shapes sent to POST /plan match the backend's pydantic models
// field-for-field.

export type SheetType = "inbody_270" | "inbody_570";

export type SegmentalLean = {
  left_arm_kg: number;
  right_arm_kg: number;
  left_leg_kg: number;
  right_leg_kg: number;
  trunk_kg: number;
};

// Canonical domain model name per CONTEXT.md and src/inform/inbody.py
export type InBodyPayload = {
  weight_kg: number;
  lean_body_mass_kg: number;
  percent_body_fat: number;
  skeletal_muscle_mass_kg: number;
  basal_metabolic_rate_kcal: number;
  segmental_lean: SegmentalLean;
  source_device: SheetType;
  // ADR-0004: optional on hardware (int | None on backend)
  visceral_fat_level: number | null;
};

// Backwards-compatibility alias for previous frontend usage
export type InBodyReading = InBodyPayload;

// Field definitions for single source of truth across Preview and Edit screens
export type ScalarInBodyField = keyof Omit<
  InBodyPayload,
  "segmental_lean" | "source_device"
>;

export type InBodyFieldMeta = {
  key: ScalarInBodyField;
  label: string;
  unit: string;
  integer?: boolean;
  formatValue?: (val: number | null) => string;
};

export const BODY_COMPOSITION_FIELDS: InBodyFieldMeta[] = [
  { key: "weight_kg", label: "Weight", unit: "kg" },
  { key: "lean_body_mass_kg", label: "Lean Body Mass", unit: "kg" },
  { key: "percent_body_fat", label: "Percent Body Fat", unit: "%" },
  { key: "skeletal_muscle_mass_kg", label: "Skeletal Muscle Mass", unit: "kg" },
  {
    key: "visceral_fat_level",
    label: "Visceral Fat Level",
    unit: "",
    integer: true,
    formatValue: (val) => (val != null ? `Level ${val}` : "—"),
  },
];

export const SEGMENTAL_LEAN_LEFT_FIELDS = [
  { key: "left_arm_kg" as const, label: "Left Arm", unit: "kg" },
  { key: "right_arm_kg" as const, label: "Right Arm", unit: "kg" },
  { key: "trunk_kg" as const, label: "Trunk", unit: "kg" },
];

export const SEGMENTAL_LEAN_RIGHT_FIELDS = [
  { key: "left_leg_kg" as const, label: "Left Leg", unit: "kg" },
  { key: "right_leg_kg" as const, label: "Right Leg", unit: "kg" },
];

// Seed values until Module 1 (OCR) is wired — same numbers as the Figma
// "Preview" mock so the screens agree with each other.
export const DEFAULT_READING: InBodyPayload = {
  weight_kg: 82,
  lean_body_mass_kg: 63.2,
  percent_body_fat: 22.9,
  skeletal_muscle_mass_kg: 36.3,
  visceral_fat_level: 7,
  basal_metabolic_rate_kcal: 1735,
  source_device: "inbody_570",
  segmental_lean: {
    left_arm_kg: 3.76,
    right_arm_kg: 3.7,
    left_leg_kg: 9.4,
    right_leg_kg: 9.44,
    trunk_kg: 28.6,
  },
};

// Re-export user and session items for convenient access and backward compatibility
export {
  type UserProfile,
  type BiologicalSex,
  type FitnessGoal,
  DEFAULT_PROFILE,
  DEFAULT_USER_NAME,
  ACTIVITY_LEVELS,
  ACTIVITY_LABELS,
} from "./user";

export { SESSION_KEYS } from "./session";
