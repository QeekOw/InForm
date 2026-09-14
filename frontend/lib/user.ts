// Mirrors inform.user.UserProfile (src/inform/user.py) verbatim.

export type BiologicalSex = "male" | "female";
export type FitnessGoal = "fat_loss" | "hypertrophy";

export type UserProfile = {
  age: number;
  biological_sex: BiologicalSex;
  activity_multiplier: number;
  fitness_goal: FitnessGoal;
};

export const DEFAULT_USER_NAME = "John Doe";

export const DEFAULT_PROFILE: UserProfile = {
  age: 30,
  biological_sex: "male",
  activity_multiplier: 1.55,
  fitness_goal: "fat_loss",
};

export const ACTIVITY_LEVELS = [
  { label: "Sedentary", multiplier: 1.2 },
  { label: "Lightly active", multiplier: 1.375 },
  { label: "Moderately active", multiplier: 1.55 },
  { label: "Very active", multiplier: 1.725 },
  { label: "Extremely active", multiplier: 1.9 },
] as const;

export const ACTIVITY_LABELS: Record<number, string> = Object.fromEntries(
  ACTIVITY_LEVELS.map((level) => [level.multiplier, level.label])
);
