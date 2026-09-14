// Mirrors inform.user.UserProfile (src/inform/user.py).

export type BiologicalSex = "male" | "female";
export type FitnessGoal = "fat_loss" | "hypertrophy";

export type UserProfile = {
  age: number;
  biological_sex: BiologicalSex;
  activity_multiplier: number;
  fitness_goal: FitnessGoal;
};

// Shown on Result when the optional name was left blank.
export const DEFAULT_USER_NAME = "Guest";

// Issue #29 story 10: five friendly labels instead of a raw multiplier. The
// hint says how often each level trains so people can place themselves.
export const ACTIVITY_LEVELS = [
  { label: "Sedentary", hint: "little or no exercise", multiplier: 1.2 },
  { label: "Lightly active", hint: "1–3x a week", multiplier: 1.375 },
  { label: "Moderately active", hint: "3–5x a week", multiplier: 1.55 },
  { label: "Very active", hint: "6–7x a week", multiplier: 1.725 },
  { label: "Extremely active", hint: "twice a day", multiplier: 1.9 },
] as const;

export const ACTIVITY_LABELS: Record<number, string> = Object.fromEntries(
  ACTIVITY_LEVELS.map((level) => [level.multiplier, level.label]),
);
