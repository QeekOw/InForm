// Where the intake flow goes next. Guests start at upload without a Profile,
// so they fill it in after confirming a reading instead of before.

import type { InBodyPayload } from "./inbody";
import type { UserProfile } from "./user";
import { loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "./session";

/** Saves the confirmed reading and returns the next route. The uploaded photo
 * is dropped here: ADR-0011 §3 keeps it only until the reading is confirmed. */
export function confirmReading(reading: InBodyPayload): string {
  saveJSON(SESSION_KEYS.reading, reading);
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
