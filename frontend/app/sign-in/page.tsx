"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import PhoneFrame from "@/components/PhoneFrame";

const imgEye = "/icons/auth/eye.svg";
const imgDivider = "/icons/auth/divider.svg";
const googleParts = [
  "/icons/auth/google-1.svg",
  "/icons/auth/google-2.svg",
  "/icons/auth/google-3.svg",
  "/icons/auth/google-4.svg",
];
const imgFacebook = "/icons/auth/facebook.svg";
const imgAppleBodyMask = "/icons/auth/apple-group.svg";
const imgAppleBody = "/icons/auth/apple-group1.svg";
const imgAppleLeaf = "/icons/auth/apple-vector.svg";

// Accounts are Phase 2 (issue #41, Neon Auth per #29) and aren't built yet,
// so every sign-in path says so instead of silently doing nothing.
const SIGN_IN_UNAVAILABLE = "isn't available yet. Continue as a guest for now.";

type FieldErrors = { email?: string; password?: string };

function GoogleLogo() {
  return (
    <div className="relative size-5 overflow-hidden">
      {googleParts.map((src) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={src} alt="" className="absolute inset-0 block size-full" src={src} />
      ))}
    </div>
  );
}

function AppleLogo() {
  return (
    <div className="relative size-5 overflow-hidden">
      <div
        className="absolute inset-[24.11%_9.2%_0_9.38%]"
        style={{
          maskImage: `url("${imgAppleBodyMask}")`,
          WebkitMaskImage: `url("${imgAppleBodyMask}")`,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleBody} />
      </div>
      <div className="absolute inset-[0_29.89%_76.91%_49.85%]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleLeaf} />
      </div>
    </div>
  );
}

const inputClass = (invalid: boolean) =>
  `h-[35px] w-full rounded-lg border bg-[#d9d9d980] px-3 text-[13px] text-gray-900 placeholder:text-gray-400 ${
    invalid ? "border-red-500" : "border-[#d9d9d9]"
  }`;

export default function SignIn() {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [notice, setNotice] = useState<string | null>(null);

  const handleLogIn = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: FieldErrors = {};
    if (!email.trim()) next.email = "Email address can't be empty.";
    if (!password) next.password = "Password can't be empty.";
    setErrors(next);
    setNotice(Object.keys(next).length === 0 ? `Signing in with email ${SIGN_IN_UNAVAILABLE}` : null);
  };

  const handleSocialSignIn = (provider: string) => {
    setErrors({});
    setNotice(`Signing in with ${provider} ${SIGN_IN_UNAVAILABLE}`);
  };

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <h1 className="mt-[118px] text-center text-[32px] font-bold tracking-[0.02em] text-[#fcfcfc]">
        Login
      </h1>

      <div className="mx-auto mt-8 w-[342px] rounded-[15px] bg-[#fcfcfc] p-[30px]">
        <form noValidate onSubmit={handleLogIn}>
          <label className="block text-[12px] text-black" htmlFor="email">
            Email Address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setErrors((prev) => ({ ...prev, email: undefined }));
            }}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
            className={`mt-[9px] ${inputClass(Boolean(errors.email))}`}
          />
          {errors.email && (
            <p id="email-error" className="mt-1 text-[10px] text-red-600">
              {errors.email}
            </p>
          )}

          <label className="mt-6 block text-[12px] text-black" htmlFor="password">
            Password
          </label>
          <div className="relative mt-[9px]">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setErrors((prev) => ({ ...prev, password: undefined }));
              }}
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? "password-error" : undefined}
              className={`pr-9 ${inputClass(Boolean(errors.password))}`}
            />
            <button
              type="button"
              aria-label="Toggle password visibility"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 size-[15px] -translate-y-1/2"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img alt="" className="size-full" src={imgEye} />
            </button>
          </div>
          {errors.password && (
            <p id="password-error" className="mt-1 text-[10px] text-red-600">
              {errors.password}
            </p>
          )}
          <p className="mt-2 text-[8px] text-[#464646] underline">Forgot Password?</p>

          <button
            type="submit"
            className="mt-[31px] flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]"
          >
            Log In
          </button>
        </form>

        {notice && (
          <p
            role="status"
            className="mt-3 rounded-lg bg-[#117d6914] px-3 py-2 text-center text-[11px] text-[#0b5c4d]"
          >
            {notice}
          </p>
        )}

        <div className="mt-[35px] flex items-center gap-[16px] opacity-60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="h-px min-w-0 flex-1" src={imgDivider} />
          <span className="text-[10px] text-black">or</span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="h-px min-w-0 flex-1" src={imgDivider} />
        </div>

        <div className="mt-[13px] flex justify-center gap-[21px]">
          <button
            type="button"
            aria-label="Continue with Google"
            onClick={() => handleSocialSignIn("Google")}
            className="flex size-10 items-center justify-center rounded-full border border-[#d9d9d9] bg-[#d9d9d980]"
          >
            <GoogleLogo />
          </button>
          <button
            type="button"
            aria-label="Continue with Apple"
            onClick={() => handleSocialSignIn("Apple")}
            className="flex size-10 items-center justify-center rounded-full border border-[#d9d9d9] bg-[#d9d9d980]"
          >
            <AppleLogo />
          </button>
          <button
            type="button"
            aria-label="Continue with Facebook"
            onClick={() => handleSocialSignIn("Facebook")}
            className="flex size-10 items-center justify-center rounded-full border border-[#d9d9d9] bg-[#d9d9d980]"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-5" src={imgFacebook} />
          </button>
        </div>

        <Link
          href="/upload"
          className="mt-[35px] flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d6936] text-[14px] font-bold tracking-[0.02em] text-[#117d69]"
        >
          Continue as a Guest
        </Link>
      </div>

      <p className="mt-8 text-center text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]">
        need an account?{" "}
        <Link href="/profile" className="underline">
          Sign Up
        </Link>
      </p>
    </PhoneFrame>
  );
}
