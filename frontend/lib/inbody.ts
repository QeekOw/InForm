// Mirrors inform.inbody.InBodyPayload / inform.user.UserProfile (src/inform)
// so the shapes sent to POST /plan match the backend's pydantic models
// field-for-field.

export type SegmentalLean = {
  left_arm_kg: number;
  right_arm_kg: number;
  left_leg_kg: number;
  right_leg_kg: number;
  trunk_kg: number;
};

export type InBodyReading = {
  weight_kg: number;
  lean_body_mass_kg: number;
  percent_body_fat: number;
  skeletal_muscle_mass_kg: number;
  basal_metabolic_rate_kcal: number;
  segmental_lean: SegmentalLean;
  source_device: "inbody_270" | "inbody_570";
  visceral_fat_level: number;
};

export type UserProfile = {
  age: number;
  biological_sex: "male" | "female";
  activity_multiplier: number;
  fitness_goal: "fat_loss" | "hypertrophy";
};

// Seed values until Module 1 (OCR) is wired — same numbers as the Figma
// "Preview" mock so the screens agree with each other.
export const DEFAULT_READING: InBodyReading = {
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

export type SampleProvenance = "synthetic" | "real";

export type SampleSheetMeta = {
  id: string;
  name: string;
  provenance: SampleProvenance;
  source_device: "inbody_270" | "inbody_570" | null;
  image_url: string;
  description: string;
};

export type SampleExtraction = {
  status: "complete" | "refused";
  data: InBodyReading | null;
  unread: string[];
  flagged: string[];
  error?: string | null;
  message?: string | null;
};

// A read the plan can be built from with no human input: nothing unread,
// nothing flagged, not refused (ADR-0008).
export function isCleanRead(extraction: SampleExtraction): boolean {
  return (
    extraction.status === "complete" &&
    extraction.data !== null &&
    extraction.unread.length === 0 &&
    extraction.flagged.length === 0
  );
}

// Every extracted value as label, value and unit.
export const READING_ROWS: {
  label: string;
  unit: string;
  value: (r: InBodyReading) => number | null;
}[] = [
  { label: "Weight", unit: "kg", value: (r) => r.weight_kg },
  { label: "Lean Body Mass", unit: "kg", value: (r) => r.lean_body_mass_kg },
  { label: "Percent Body Fat", unit: "%", value: (r) => r.percent_body_fat },
  { label: "Skeletal Muscle Mass", unit: "kg", value: (r) => r.skeletal_muscle_mass_kg },
  { label: "Basal Metabolic Rate", unit: "kcal", value: (r) => r.basal_metabolic_rate_kcal },
  { label: "Visceral Fat Level", unit: "level", value: (r) => r.visceral_fat_level },
  { label: "Left Arm", unit: "kg", value: (r) => r.segmental_lean.left_arm_kg },
  { label: "Right Arm", unit: "kg", value: (r) => r.segmental_lean.right_arm_kg },
  { label: "Left Leg", unit: "kg", value: (r) => r.segmental_lean.left_leg_kg },
  { label: "Right Leg", unit: "kg", value: (r) => r.segmental_lean.right_leg_kg },
  { label: "Trunk", unit: "kg", value: (r) => r.segmental_lean.trunk_kg },
];

export const SESSION_KEYS = {
  profile: "inform:profile",
  reading: "inform:reading",
  sheetType: "inform:sheetType",
  name: "inform:name",
  sampleId: "inform:sampleId",
  extraction: "inform:extraction",
} as const;
