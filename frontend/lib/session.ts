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
  sheetPages: "inform:sheetPages",
  sheetSource: "inform:sheetSource",
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
  // A one-shot message handed to the next screen, so a redirect can explain
  // itself instead of dumping someone back at the gallery with no reason.
  // Read and removed by whoever displays it.
  notice: "inform:notice",
  // In-app routes visited this session, so the Back control can tell whether
  // going back would land inside the app or outside it (components/BackButton).
  backTrail: "inform:backTrail",
  // The written plan and its provenance, handed from Result to its own Summary
  // view so reading the prose doesn't mean recomputing the plan (or paying for a
  // second LLM call) to get it.
  narrative: "inform:narrative",
  // Redirect target after sign-in or sign-up (e.g. returning to /result to save a scan)
  nextAfterAuth: "inform:nextAfterAuth",
  // Bearer authentication token for cross-origin and persistent API calls
  authToken: "inform:authToken",
  // Cached account session data
  account: "inform:account",
  // Set once the Student Project & Privacy Notice has been acknowledged this
  // session, so it is shown before the first upload or camera use only.
  privacyAck: "inform:privacyAck",
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
    SESSION_KEYS.sheetPages,
    SESSION_KEYS.sheetSource,
    SESSION_KEYS.measured,
    SESSION_KEYS.reading,
    SESSION_KEYS.corrections,
    SESSION_KEYS.confirmations,
    SESSION_KEYS.readId,
    SESSION_KEYS.nextAfterProfile,
    SESSION_KEYS.nextAfterAuth,
    // The plan's prose belongs to the reading that produced it, so it goes too.
    SESSION_KEYS.narrative,
  ]) {
    removeSessionItem(key);
  }
}

/** Complete state cleanup across both sessionStorage and localStorage (e.g. on signOut or guest reset) */
export function clearAllSession(): void {
  try {
    sessionStorage.clear();
  } catch {}
  try {
    localStorage.clear();
  } catch {}
}
