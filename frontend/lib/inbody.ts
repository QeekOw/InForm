// Mirrors inform.inbody.InBodyPayload (src/inform/inbody.py) so the reading
// sent to POST /plan matches the backend's pydantic model field for field.

export type SheetType = "inbody_270";

export type SegmentalLean = {
  left_arm_kg: number;
  right_arm_kg: number;
  left_leg_kg: number;
  right_leg_kg: number;
  trunk_kg: number;
};

export type InBodyPayload = {
  weight_kg: number;
  lean_body_mass_kg: number;
  percent_body_fat: number;
  skeletal_muscle_mass_kg: number;
  basal_metabolic_rate_kcal: number;
  segmental_lean: SegmentalLean;
  source_device: SheetType;
  // ADR-0004: optional on both devices (int | None on the backend).
  visceral_fat_level: number | null;
};

export type ScalarInBodyField = Exclude<keyof InBodyPayload, "segmental_lean" | "source_device">;
export type SegmentalLeanField = keyof SegmentalLean;

export type FieldMeta<K extends string> = {
  key: K;
  label: string;
  unit: string;
  integer?: boolean;
  formatValue?: (value: number) => string;
};

// Display order shared by Preview and Edit.
export const BODY_COMPOSITION_FIELDS: FieldMeta<ScalarInBodyField>[] = [
  { key: "weight_kg", label: "Weight", unit: "kg" },
  { key: "lean_body_mass_kg", label: "Lean Body Mass", unit: "kg" },
  { key: "percent_body_fat", label: "Percent Body Fat", unit: "%" },
  { key: "skeletal_muscle_mass_kg", label: "Skeletal Muscle Mass", unit: "kg" },
  {
    key: "visceral_fat_level",
    label: "Visceral Fat Level",
    unit: "",
    integer: true,
    formatValue: (value) => `Level ${value}`,
  },
];

// The two columns of the Segmental Lean Analysis card.
export const SEGMENTAL_LEAN_COLUMNS: FieldMeta<SegmentalLeanField>[][] = [
  [
    { key: "left_arm_kg", label: "Left Arm", unit: "kg" },
    { key: "right_arm_kg", label: "Right Arm", unit: "kg" },
    { key: "trunk_kg", label: "Trunk", unit: "kg" },
  ],
  [
    { key: "left_leg_kg", label: "Left Leg", unit: "kg" },
    { key: "right_leg_kg", label: "Right Leg", unit: "kg" },
  ],
];

export const BMR_FIELD: FieldMeta<ScalarInBodyField> = {
  key: "basal_metabolic_rate_kcal",
  label: "Basal Metabolic Rate",
  unit: "kcal",
};

// What the Edit form holds: any field can be blank while someone is typing.
export type InBodyDraft = Omit<InBodyPayload, ScalarInBodyField | "segmental_lean"> & {
  [K in ScalarInBodyField]: number | null;
} & {
  segmental_lean: { [K in SegmentalLeanField]: number | null };
};

/** Labels of required fields left blank, in display order. Visceral Fat Level
 * is the only optional field (ADR-0004). */
export function blankRequiredFields(draft: InBodyDraft): string[] {
  const scalars = [...BODY_COMPOSITION_FIELDS, BMR_FIELD].filter(
    (field) => field.key !== "visceral_fat_level" && draft[field.key] === null,
  );
  const segments = SEGMENTAL_LEAN_COLUMNS.flat().filter(
    (field) => draft.segmental_lean[field.key] === null,
  );
  return [...scalars, ...segments].map((field) => field.label);
}

// Seed values for an uploaded sheet until Module 1 (OCR) is wired: the
// numbers from the Figma "Preview" mock, on the InBody 270 layout.
export const DEFAULT_READING: InBodyPayload = {
  weight_kg: 82,
  lean_body_mass_kg: 63.2,
  percent_body_fat: 22.9,
  skeletal_muscle_mass_kg: 36.3,
  visceral_fat_level: 7,
  basal_metabolic_rate_kcal: 1735,
  source_device: "inbody_270",
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
  source_device: SheetType | null;
  image_url: string;
  description: string;
};

export type SampleExtraction = {
  status: "complete" | "refused";
  data: InBodyPayload | null;
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
  value: (r: InBodyPayload) => number | null;
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
