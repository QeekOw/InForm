// Mirrors backend/main.py's Account-related endpoints (issue #41). Every
// call here sends the session cookie (via apiFetch's credentials: "include")
// so a signed-in person is recognized on this and every future request.

import { apiDelete, apiGet, apiPatch, apiPost } from "./api";
import type { BiologicalSex, FitnessGoal } from "./user";

/** Profile values stored on an Account purely to pre-fill a form.
 *
 * Mirrors backend/main.py's AccountProfileDefaults. Never the source of truth
 * for a past plan — a Scan's own frozen profile snapshot is (issue #42) — and
 * every field is optional, since the whole flow works without an account at all.
 */
export type AccountProfileDefaults = {
  date_of_birth: string | null;
  /** Display only. Never used in any plan calculation. */
  height_cm: number | null;
  default_biological_sex: BiologicalSex | null;
  default_activity_multiplier: number | null;
  default_fitness_goal: FitnessGoal | null;
  /** Display name for greetings and the profile page. Never used by the pipeline. */
  name: string | null;
};

export type Account = AccountProfileDefaults & {
  id: string;
  email: string;
  created_at: string;
  token?: string | null;
};

/** What the sign-up form collects, in one request (Requirement 3.1). */
export type SignupPayload = Partial<AccountProfileDefaults> & {
  email: string;
  password: string;
};

export function signup(payload: SignupPayload): Promise<Account> {
  return apiPost<Account>("/auth/signup", payload);
}

export function login(email: string, password: string): Promise<Account> {
  return apiPost<Account>("/auth/login", { email, password });
}

export function logout(): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/auth/logout");
}

export function updateProfile(payload: Partial<AccountProfileDefaults>): Promise<Account> {
  return apiPatch<Account>("/auth/me", payload);
}

/** Change the sign-in email and/or password. The current password is always
 * required (403 when wrong, 409 when the new email is taken). */
export function updateCredentials(payload: {
  current_password: string;
  new_email?: string;
  new_password?: string;
}): Promise<Account> {
  return apiPatch<Account>("/auth/credentials", payload);
}

/** Returns null (rather than throwing) when nobody is signed in, so callers
 * can treat "not signed in" as a normal state instead of an error path. */
export async function me(): Promise<Account | null> {
  try {
    return await apiGet<Account>("/auth/me");
  } catch {
    return null;
  }
}

/** Permanently deletes the signed-in person's Account and every Scan
 * belonging to it (issue #44). Irreversible. */
export function deleteAccount(): Promise<void> {
  return apiDelete<void>("/account");
}
