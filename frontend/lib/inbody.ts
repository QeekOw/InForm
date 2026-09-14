// Mirrors inform.inbody.InBodyPayload (src/inform/inbody.py) so the reading
// sent to POST /plan matches the backend's pydantic model field for field.

export type SheetType = "inbody_270" | "inbody_570";

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

// Seed values until Module 1 (OCR) is wired: the numbers from the Figma
// "Preview" mock, on the InBody 270 layout the upload screen offers.
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
