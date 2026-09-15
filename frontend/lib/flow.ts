// Where the intake flow goes next. Guests start at upload without a Profile,
// so they fill it in after confirming a reading instead of before.

import type { InBodyPayload, PartialInBody } from "./inbody";
import type { UserProfile } from "./user";
import { loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "./session";

/** Saves the confirmed reading, original measured values, and optional corrections, and returns the next route.
 * Corrected fields are stored alongside measured fields, never merged into them. */
export function confirmReading(
  reading: InBodyPayload,
  corrections?: Record<string, number | { value: number; unit?: string }>,
  measured?: PartialInBody | null,
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
  removeSessionItem(SESSION_KEYS.photo);
  if (loadJSON<UserProfile>(SESSION_KEYS.profile)) return "/result";
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
  const next = isFinishingGuestPlan() ? "/result" : "/upload";
  removeSessionItem(SESSION_KEYS.nextAfterProfile);
  return next;
}
