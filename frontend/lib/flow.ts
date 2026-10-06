import type { Account } from "./auth";
import type { InBodyPayload, PartialInBody } from "./inbody";
import type { UserProfile } from "./user";
import { ageFromDob } from "./user";
import { loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "./session";

/** Saves the confirmed reading, original measured values, and optional corrections or confirmations, and returns the next route.
 * Corrected fields are stored alongside measured fields, never merged into them. */
export function confirmReading(
  reading: InBodyPayload,
  corrections?: Record<string, number | { value: number; unit?: string }>,
  measured?: PartialInBody | null,
  confirmations?: string[],
): string {
  saveJSON(SESSION_KEYS.reading, reading);
  if (measured) {
    saveJSON(SESSION_KEYS.measured, measured);
  }
  if (corrections && Object.keys(corrections).length > 0) {
    saveJSON(SESSION_KEYS.corrections, corrections);
  } else {
    removeSessionItem(SESSION_KEYS.corrections);
  }
  if (confirmations && confirmations.length > 0) {
    saveJSON(SESSION_KEYS.confirmations, confirmations);
  } else {
    removeSessionItem(SESSION_KEYS.confirmations);
  }
  removeSessionItem(SESSION_KEYS.photo);

  if (loadJSON<UserProfile>(SESSION_KEYS.profile)) return "/result";

  const acc = loadJSON<Account>(SESSION_KEYS.account);
  if (
    acc &&
    acc.date_of_birth &&
    acc.default_biological_sex &&
    acc.default_activity_multiplier &&
    acc.default_fitness_goal
  ) {
    const age = ageFromDob(acc.date_of_birth);
    if (age !== null) {
      const profile: UserProfile = {
        age,
        biological_sex: acc.default_biological_sex,
        activity_multiplier: acc.default_activity_multiplier,
        fitness_goal: acc.default_fitness_goal,
      };
      saveJSON(SESSION_KEYS.profile, profile);
      return "/result";
    }
  }

  saveJSON(SESSION_KEYS.nextAfterProfile, "/result");
  return "/profile";
}

/** True while a guest is filling in the Profile on their way to the plan. */
export function isFinishingGuestPlan(): boolean {
  return loadJSON<string>(SESSION_KEYS.nextAfterProfile) === "/result";
}

/** Returns the route after Profile: the plan for a guest who already confirmed
 * a reading, otherwise upload. */
export function nextAfterProfile(): string {
  const reading = loadJSON(SESSION_KEYS.reading);
  const next = isFinishingGuestPlan() || Boolean(reading) ? "/result" : "/upload";
  removeSessionItem(SESSION_KEYS.nextAfterProfile);
  return next;
}
