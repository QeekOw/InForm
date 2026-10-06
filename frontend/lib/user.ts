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

// --- Date of birth ---------------------------------------------------------
//
// A Scan freezes the *age* it was taken at, not a birth date. The date of birth
// exists so nobody has to work their own age out, and so "an implausible age is
// rejected before a plan is computed" (issue #34) can be checked at the point of
// entry. Mirrors the bounds enforced by backend/main.py's AccountProfileDefaults,
// which is what actually decides — this is the immediate answer, not the gate.

export const MIN_AGE = 13;
export const MAX_AGE = 100;

/** Today as `YYYY-MM-DD`, for a date input's `max`. */
export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Completed years since `dob`, or null if it isn't a usable date. */
export function ageFromDob(dob: string): number | null {
  if (!dob) return null;
  const birth = new Date(dob);
  if (Number.isNaN(birth.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const hasHadBirthdayThisYear =
    now.getMonth() > birth.getMonth() ||
    (now.getMonth() === birth.getMonth() && now.getDate() >= birth.getDate());
  if (!hasHadBirthdayThisYear) age -= 1;
  return age;
}

/** The age a date of birth implies, or the reason it can't be used. */
export function validateDateOfBirth(
  dob: string,
): { age: number; error: null } | { age: null; error: string } {
  const age = ageFromDob(dob);
  if (age === null) return { age: null, error: "Enter your date of birth." };
  if (age < MIN_AGE || age > MAX_AGE) {
    return {
      age: null,
      error: `Enter a date of birth that makes you between ${MIN_AGE} and ${MAX_AGE}.`,
    };
  }
  return { age, error: null };
}

// --- Height ----------------------------------------------------------------
//
// Display only. Nothing in the pipeline consumes it: Katch-McArdle works from
// lean body mass, and no BMI or other height-derived clinical metric is computed.
// These bounds are a typo gate, not a clinical range, and mirror the backend's.

export const MIN_HEIGHT_CM = 50;
export const MAX_HEIGHT_CM = 260;

/** A typed height as a number, or the reason it can't be used. Blank is fine:
 * height is optional, so `{ heightCm: null, error: null }` means "not given". */
export function validateHeightCm(
  raw: string,
): { heightCm: number | null; error: null } | { heightCm: null; error: string } {
  const trimmed = raw.trim();
  if (!trimmed) return { heightCm: null, error: null };
  const value = Number(trimmed);
  if (!Number.isFinite(value)) return { heightCm: null, error: "Enter height as a number." };
  if (value < MIN_HEIGHT_CM || value > MAX_HEIGHT_CM) {
    return {
      heightCm: null,
      error: `Enter a height between ${MIN_HEIGHT_CM} and ${MAX_HEIGHT_CM} cm.`,
    };
  }
  return { heightCm: value, error: null };
}
