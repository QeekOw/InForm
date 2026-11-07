import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import AccountSettings from "@/app/account/page";
import Home from "@/app/page";
import { AuthProvider, useAuth } from "./AuthProvider";
import type { Account } from "./auth";
import { SESSION_KEYS } from "./session";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

const account: Account = {
  id: "account-1",
  email: "person@example.test",
  created_at: "2026-11-07T00:00:00Z",
  name: "Person",
  date_of_birth: "1990-01-01",
  height_cm: null,
  default_biological_sex: "male",
  default_activity_multiplier: 1.55,
  default_fitness_goal: "hypertrophy",
};

function AuthState() {
  const { account, loading } = useAuth();
  return createElement("p", null, account?.email ?? "Guest", loading ? " loading" : " ready");
}

afterEach(() => vi.unstubAllGlobals());

describe("initial auth rendering", () => {
  it("matches the server markup even with a cached browser account", () => {
    const server = renderToString(createElement(AuthProvider, null, createElement(AuthState)));
    vi.stubGlobal("window", {});
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => key === SESSION_KEYS.account ? JSON.stringify(account) : null,
      setItem: vi.fn(),
    });

    const browser = renderToString(createElement(AuthProvider, null, createElement(AuthState)));

    expect(browser).toBe(server);
    expect(browser).toContain("Guest");
    expect(browser).toContain("loading");
    expect(sessionStorage.setItem).not.toHaveBeenCalled();
  });

  it("renders identical initial markup for /account on server and client when an account is cached", () => {
    const server = renderToString(createElement(AuthProvider, null, createElement(AccountSettings)));
    vi.stubGlobal("window", {});
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => key === SESSION_KEYS.account ? JSON.stringify(account) : null,
      setItem: vi.fn(),
    });

    const browser = renderToString(createElement(AuthProvider, null, createElement(AccountSettings)));

    expect(browser).toBe(server);
    expect(browser).toContain("Loading your profile…");
  });

  it("renders a usable start link before authentication resolves", () => {
    const html = renderToString(createElement(AuthProvider, null, createElement(Home)));

    expect(html).toContain("Get Started");
    expect(html).toContain("href=\"/sign-in?start=1\"");
  });
});
