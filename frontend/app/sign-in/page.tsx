"use client";

import { useState, Suspense, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import BackButton from "@/components/BackButton";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, Card, GoogleLogo, OrDivider, PasswordField, PhotoBackdrop, TextField } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { loadJSON, removeSessionItem, SESSION_KEYS } from "@/lib/session";

// Shown but not built yet: both say so plainly instead of doing nothing.
const GOOGLE_UNAVAILABLE =
  "Google sign-in isn't available yet. Use your email and password, or continue as a guest.";
const RESET_UNAVAILABLE =
  "Password reset isn't available yet. If you're stuck, continue as a guest — no account is needed to get a plan.";

type FieldErrors = { email?: string; password?: string };

function SignInContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isSavingScan = redirectParam?.includes("/result") ?? false;

  const handleLogIn = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: FieldErrors = {};
    if (!email.trim()) next.email = "Email address can't be empty.";
    if (!password) next.password = "Password can't be empty.";
    setErrors(next);
    setNotice(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await signIn(email, password);
      const target = redirectParam || loadJSON<string>(SESSION_KEYS.nextAfterAuth) || "/dashboard";
      removeSessionItem(SESSION_KEYS.nextAfterAuth);
      router.push(target);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setNotice(typeof err.detail === "string" ? err.detail : "Incorrect email or password.");
      } else {
        setNotice("Something went wrong signing in. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const signUpHref = redirectParam
    ? `/sign-up?redirect=${encodeURIComponent(redirectParam)}`
    : "/sign-up";

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <PhotoBackdrop src="/bg/login.jpg" className="absolute inset-0 min-h-full" />

      <div className="relative px-[30px] pb-[40px] pt-[48px]">
        <BackButton href={redirectParam || "/"} />

        <h1 className="mt-[72px] text-center text-[40px] font-bold tracking-[0.02em] text-[#fcfcfc]">
          Login
        </h1>
        {isSavingScan && (
          <p className="mt-1 text-center text-[12px] font-medium text-[#7ee0cf]">
            Sign in to save your scan to your history
          </p>
        )}

        <Card className="mt-[36px] p-[30px]">
          <form noValidate onSubmit={handleLogIn} className="space-y-[15px]">
            <TextField
              label="Email Address"
              icon="email"
              type="email"
              autoComplete="email"
              placeholder="Enter your email address"
              value={email}
              error={errors.email}
              onChange={(e) => {
                setEmail(e.target.value);
                setErrors((p) => ({ ...p, email: undefined }));
              }}
            />
            <PasswordField
              label="Password"
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              error={errors.password}
              onChange={(e) => {
                setPassword(e.target.value);
                setErrors((p) => ({ ...p, password: undefined }));
              }}
              hint={
                <button
                  type="button"
                  onClick={() => setNotice(RESET_UNAVAILABLE)}
                  className="mt-[5px] text-[9px] text-[#464646] underline hover:text-black"
                >
                  Forgot Password?
                </button>
              }
            />
            <button type="submit" disabled={submitting} className={`${btn.primary} !mt-[26px]`}>
              {submitting ? "Signing in…" : "Log In"}
            </button>
          </form>

          {notice && (
            <p
              role="status"
              className="mt-3 rounded-[8px] bg-[#117d69]/10 px-3 py-2 text-center text-[11px] text-[#0b5c4d]"
            >
              {notice}
            </p>
          )}

          <div className="my-[30px] text-black">
            <OrDivider />
          </div>

          <button
            type="button"
            onClick={() => {
              setErrors({});
              setNotice(GOOGLE_UNAVAILABLE);
            }}
            className={`${btn.secondary} font-medium`}
          >
            <GoogleLogo />
            Continue with Google
          </button>

          <Link
            href={redirectParam || "/upload"}
            className={`${btn.soft} mt-[8px] h-auto flex-col gap-[3px] py-[10px]`}
          >
            {redirectParam ? "Return to your scan" : "Continue as a Guest"}
            <span className="max-w-[160px] text-center text-[9px] font-medium leading-tight">
              No account needed to get a plan. An account only saves your scans.
            </span>
          </Link>
        </Card>

        <p className="mt-[26px] text-center text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]">
          Need an account?{" "}
          <Link href={signUpHref} className="underline">
            Sign Up
          </Link>
        </p>
      </div>
    </PhoneFrame>
  );
}

export default function SignIn() {
  return (
    <Suspense
      fallback={
        <PhoneFrame bg="bg-[#3e3e3e]">
          <div className="flex h-full items-center justify-center text-[14px] text-white">
            Loading…
          </div>
        </PhoneFrame>
      }
    >
      <SignInContent />
    </Suspense>
  );
}
