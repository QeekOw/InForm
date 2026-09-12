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

export const SESSION_KEYS = {
  profile: "inform:profile",
  reading: "inform:reading",
  sheetType: "inform:sheetType",
  name: "inform:name",
} as const;
