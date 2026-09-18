// Client-only session storage helpers. Used to carry the Profile and
// (possibly corrected) InBody reading across the static routes between
// /profile and /result — there's no server-side session yet (Track B
// accounts/persistence lands in issues #41-#44), so this is the "fast and
// rough" stand-in the walking-skeleton era calls for.

export const SESSION_KEYS = {
  profile: "inform:profile",
  reading: "inform:reading",
  name: "inform:name",
  photo: "inform:photo",
  // The picked Sample sheet and its stored read (issue #35).
  sampleId: "inform:sampleId",
  extraction: "inform:extraction",
  // Machine-measured values from OCR / sample sheet (stored alongside corrections, never merged)
  measured: "inform:measured",
  // Human corrections typed off the sheet or edited (recorded alongside measured fields)
  corrections: "inform:corrections",
  // Confirmations of unchanged flagged fields (issue #39)
  confirmations: "inform:confirmations",
  // Live or stored read job identifier (issue #40)
  readId: "inform:readId",
  // Set when a guest confirms a reading before filling in a Profile, so
  // Profile continues to the plan instead of back to upload.
  nextAfterProfile: "inform:nextAfterProfile",
} as const;

export function saveJSON(key: string, value: unknown): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // sessionStorage unavailable (private mode, etc.) — the app still works,
    // downstream pages just fall back to their defaults.
  }
}

export function loadJSON<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function removeSessionItem(key: string): void {
  try {
    sessionStorage.removeItem(key);
  } catch {
    // sessionStorage unavailable — nothing was stored to remove.
  }
}

// A new photo or Sample sheet pick replaces the previous attempt, so an
// earlier sheet's image, read or flags never show up next to the new one.
export function clearSheet(): void {
  for (const key of [
    SESSION_KEYS.photo,
    SESSION_KEYS.sampleId,
    SESSION_KEYS.extraction,
    SESSION_KEYS.measured,
    SESSION_KEYS.reading,
    SESSION_KEYS.corrections,
    SESSION_KEYS.confirmations,
    SESSION_KEYS.readId,
  ]) {
    removeSessionItem(key);
  }
}
