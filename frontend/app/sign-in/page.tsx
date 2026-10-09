"use client";

import { useEffect, useState, Suspense, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import BackButton from "@/components/BackButton";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, Card, GoogleLogo, OrDivider, PasswordField, PhotoBackdrop, TextField } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { googleSignInStatusMessage, googleSignInUrl } from "@/lib/googleAuth";
import { loadJSON, removeSessionItem, SESSION_KEYS } from "@/lib/session";

const RESET_UNAVAILABLE =
  "Password reset isn't available yet. If you're stuck, continue as a guest — no account is needed to get a plan.";

type FieldErrors = { email?: string; password?: string };

function SignInContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");
  const googleStatus = searchParams.get("google");
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [notice, setNotice] = useState<string | null>(() =>
    googleSignInStatusMessage(googleStatus),
  );
  const [submitting, setSubmitting] = useState(false);

  const isSavingScan = redirectParam?.includes("/result") ?? false;

  useEffect(() => {
    if (googleStatus !== "success") return;
    const target = redirectParam || loadJSON<string>(SESSION_KEYS.nextAfterAuth) || "/dashboard";
    removeSessionItem(SESSION_KEYS.nextAfterAuth);
    router.replace(target);
  }, [googleStatus, redirectParam, router]);

  const handleLogIn = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting) return;
    const next: FieldErrors = {};
    const normalizedEmail = email.trim();
    if (!normalizedEmail) next.email = "Email address can't be empty.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      next.email = "Enter a valid email address.";
    }
    if (!password) next.password = "Password can't be empty.";
    setErrors(next);
    setNotice(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await signIn(normalizedEmail, password);
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
      <PhotoBackdrop src="/bg/login.jpg" className="absolute inset-0" />

      <div className="sign-in-layout relative z-10">
        <BackButton href={redirectParam || "/"} />

        <h1 className="sign-in-title text-center font-bold tracking-[0.02em] text-[#fcfcfc]">
          Login
        </h1>
        {isSavingScan && (
          <p className="mt-1 text-center text-[12px] font-medium text-[#7ee0cf]">
            Sign in to save your scan to your history
          </p>
        )}

        <Card className="sign-in-card">
          <form noValidate onSubmit={handleLogIn} className="sign-in-form">
            <TextField
              label="Email Address"
              icon="email"
              type="email"
              autoComplete="email"
              autoCapitalize="none"
              inputMode="email"
              enterKeyHint="next"
              required
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
              enterKeyHint="go"
              required
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
                  className="sign-in-forgot underline"
                >
                  Forgot Password?
                </button>
              }
            />
            <button
              type="submit"
              disabled={submitting}
              className={`${btn.primary} sign-in-submit`}
              aria-busy={submitting}
            >
              {submitting ? "Signing in…" : "Log In"}
            </button>
          </form>

          {notice && (
            <p
              role="status"
              aria-live="polite"
              className="sign-in-notice mt-3 rounded-[8px] bg-[#117d69]/10 px-3 py-2 text-center text-[#0b5c4d]"
            >
              {notice}
            </p>
          )}

          <div className="sign-in-divider text-black">
            <OrDivider />
          </div>

          <a
            href={googleSignInUrl(
              redirectParam,
            )}
            onClick={(event) => {
              if (redirectParam) return;
              const next = loadJSON<string>(SESSION_KEYS.nextAfterAuth);
              if (!next) return;
              event.preventDefault();
              window.location.assign(googleSignInUrl(next));
            }}
            className={`${btn.secondary} sign-in-google font-medium`}
          >
            <GoogleLogo />
            Continue with Google
          </a>

          <Link
            href={redirectParam || "/upload"}
            className={`${btn.soft} sign-in-guest`}
          >
            {redirectParam ? "Return to your scan" : "Continue as a Guest"}
          </Link>
        </Card>

        <p className="sign-in-footer text-center font-bold tracking-[0.02em] text-[#fcfcfc]">
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
        <PhoneFrame bg="bg-[#3e3e3e]" scrollable={false}>
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
