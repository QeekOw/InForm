"use client";

// Small auth context (issue #41): checks /auth/me once on mount, exposes the
// signed-in Account (or null for a guest) plus signIn/signUp/signOut actions
// that keep every consumer in sync without each page re-fetching /auth/me.

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as authApi from "./auth";
import type { Account, SignupPayload } from "./auth";
import { clearAllSession, loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "./session";
import { ageFromDob, type UserProfile } from "./user";

type AuthContextValue = {
  account: Account | null;
  // True only during the initial /auth/me check on mount, so pages can avoid
  // flashing a signed-out state before that check resolves.
  loading: boolean;
  signIn: (email: string, password: string) => Promise<Account>;
  /** One request carrying credentials and profile defaults together, so nothing
   * has to be asked twice (Requirement 3.1). */
  signUp: (payload: SignupPayload) => Promise<Account>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function syncProfileFromAccount(acc: Account | null) {
  if (!acc) return;
  if (acc.name) saveJSON(SESSION_KEYS.name, acc.name);
  if (
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
    }
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<Account | null>(() => {
    if (typeof window !== "undefined") {
      const cached = loadJSON<Account>(SESSION_KEYS.account);
      if (cached) {
        syncProfileFromAccount(cached);
        return cached;
      }
    }
    return null;
  });
  const [loading, setLoading] = useState(true);

  const updateAccount = useCallback((nextAccount: Account | null) => {
    setAccount(nextAccount);
    if (nextAccount) {
      saveJSON(SESSION_KEYS.account, nextAccount);
      if (nextAccount.token) {
        saveJSON(SESSION_KEYS.authToken, nextAccount.token);
      }
      syncProfileFromAccount(nextAccount);
    } else {
      removeSessionItem(SESSION_KEYS.account);
      removeSessionItem(SESSION_KEYS.authToken);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const fresh = await authApi.me();
      updateAccount(fresh);
    } catch {
      updateAccount(null);
    }
  }, [updateAccount]);

  useEffect(() => {
    let active = true;
    authApi.me().then((result) => {
      if (active) {
        updateAccount(result);
        setLoading(false);
      }
    });

    const handleStorage = (e: StorageEvent) => {
      if (e.key === SESSION_KEYS.account || e.key === SESSION_KEYS.authToken) {
        const current = loadJSON<Account>(SESSION_KEYS.account);
        setAccount(current);
        syncProfileFromAccount(current);
      }
    };
    window.addEventListener("storage", handleStorage);

    return () => {
      active = false;
      window.removeEventListener("storage", handleStorage);
    };
  }, [updateAccount]);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    updateAccount(result);
    return result;
  }, [updateAccount]);

  const signUp = useCallback(async (payload: SignupPayload) => {
    const result = await authApi.signup(payload);
    updateAccount(result);
    return result;
  }, [updateAccount]);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      updateAccount(null);
      clearAllSession();
    }
  }, [updateAccount]);

  return (
    <AuthContext.Provider value={{ account, loading, signIn, signUp, signOut, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
