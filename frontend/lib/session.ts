// Client-only session storage helpers. Used to carry the Profile and
// (possibly corrected) InBody reading across the static routes between
// /profile and /result — there's no server-side session yet (Track B
// accounts/persistence lands in issues #41-#44), so this is the "fast and
// rough" stand-in the walking-skeleton era calls for.

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
