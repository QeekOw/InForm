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

      <div className="relative flex min-h-full flex-col px-[30px] pb-[40px] pt-[48px]">
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

          <a
            href={googleSignInUrl(
              redirectParam || loadJSON<string>(SESSION_KEYS.nextAfterAuth),
            )}
            className={`${btn.secondary} font-medium`}
          >
            <GoogleLogo />
            Continue with Google
          </a>

          <Link
            href={redirectParam || "/upload"}
            className={`${btn.soft} mt-[8px]`}
          >
            {redirectParam ? "Return to your scan" : "Continue as a Guest"}
          </Link>
        </Card>

        <p className="mt-auto pt-[26px] text-center text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]">
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
