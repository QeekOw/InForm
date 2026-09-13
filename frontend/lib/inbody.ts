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

export const DEFAULT_PROFILE: UserProfile = {
  age: 30,
  biological_sex: "male",
  activity_multiplier: 1.55,
  fitness_goal: "fat_loss",
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
  data: Partial<InBodyReading> | null;
  unread: string[];
  flagged: string[];
  error?: string | null;
  message?: string | null;
};

export const DEFAULT_SAMPLES: SampleSheetMeta[] = [
  {
    id: "synthetic_270_clean",
    name: "Synthetic InBody 270 (Clean)",
    provenance: "synthetic",
    source_device: "inbody_270",
    image_url: "/samples/synthetic_270_clean/image",
    description: "Clean synthetic InBody 270 scan; all required fields read without flags.",
  },
  {
    id: "synthetic_570_clean",
    name: "Synthetic InBody 570 (Clean)",
    provenance: "synthetic",
    source_device: "inbody_570",
    image_url: "/samples/synthetic_570_clean/image",
    description: "Clean synthetic InBody 570 scan; includes segmental lean analysis and visceral fat level.",
  },
  {
    id: "real_270_clean",
    name: "Real InBody 270 Printout (Redacted, Misread LBM)",
    provenance: "real",
    source_device: "inbody_270",
    image_url: "/samples/real_270_clean/image",
    description: "Genuine InBody 270 printout held with subject consent; member ID and gym name are fully redacted (ADR-0011). Triggers cross-check flags due to misread LBM.",
  },
  {
    id: "real_270_flagged",
    name: "Real InBody 270 Printout (Flagged LBM, Redacted)",
    provenance: "real",
    source_device: "inbody_270",
    image_url: "/samples/real_270_flagged/image",
    description: "Genuine InBody 270 printout held with subject consent; member ID and gym name are fully redacted (ADR-0011). Triggers deterministic physiological cross-check flags.",
  },
  {
    id: "refused_non_sheet",
    name: "Non-InBody Document (Refusal)",
    provenance: "synthetic",
    source_device: null,
    image_url: "/samples/refused_non_sheet/image",
    description: "Non-InBody document correctly declined by the extraction model (fail-closed refusal).",
  },
];

export const SESSION_KEYS = {
  profile: "inform:profile",
  reading: "inform:reading",
  sheetType: "inform:sheetType",
  name: "inform:name",
  sampleId: "inform:sampleId",
  extraction: "inform:extraction",
} as const;
