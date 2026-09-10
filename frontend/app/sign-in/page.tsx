"use client";

import { useState } from "react";
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
const imgAppleGroup = "/icons/auth/apple-group.svg";
const imgAppleGroup1 = "/icons/auth/apple-group1.svg";
const imgAppleVector = "/icons/auth/apple-vector.svg";
const imgAppleGroup2 = "/icons/auth/apple-group2.svg";
const imgAppleGroup3 = "/icons/auth/apple-group3.svg";
const imgAppleVector1 = "/icons/auth/apple-vector1.svg";
const imgAppleVector3 = "/icons/auth/apple-vector3.svg";
const imgAppleVector4 = "/icons/auth/apple-vector4.svg";

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
        style={{ maskImage: `url("${imgAppleGroup}")`, WebkitMaskImage: `url("${imgAppleGroup}")` }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleGroup1} />
      </div>
      <div className="absolute inset-[0_29.89%_76.91%_49.85%]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleVector} />
      </div>
      <div
        className="absolute inset-[5.94%_-398.11%_-109.28%_279.94%]"
        style={{ maskImage: `url("${imgAppleGroup2}")`, WebkitMaskImage: `url("${imgAppleGroup2}")` }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleGroup3} />
      </div>
      <div className="absolute inset-[-58.66%_-342.66%_96.8%_388.37%]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleVector1} />
      </div>
      <div className="absolute inset-[14.62%_-569.88%_-64.07%_544.84%]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleVector3} />
      </div>
      <div className="absolute inset-[6.64%_-963.21%_-107.94%_684.13%]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-0 block size-full" src={imgAppleVector4} />
      </div>
    </div>
  );
}

export default function SignIn() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <h1 className="mt-[118px] text-center text-[32px] font-bold tracking-[0.02em] text-[#fcfcfc]">
        Login
      </h1>

      <div className="mx-auto mt-8 w-[342px] rounded-[15px] bg-[#fcfcfc] p-[30px]">
        <label className="block text-[12px] text-black" htmlFor="email">
          Email Address
        </label>
        <input
          id="email"
          type="email"
          className="mt-[9px] h-[35px] w-full rounded-lg border border-[#d9d9d9] bg-[#d9d9d980] px-3 text-[13px]"
        />

        <label className="mt-6 block text-[12px] text-black" htmlFor="password">
          Password
        </label>
        <div className="relative mt-[9px]">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            className="h-[35px] w-full rounded-lg border border-[#d9d9d9] bg-[#d9d9d980] px-3 pr-9 text-[13px]"
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
        <p className="mt-2 text-[8px] text-[#464646] underline">Forgot Password?</p>

        <button
          type="button"
          className="mt-[31px] flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]"
        >
          Log In
        </button>

        <div className="mt-[35px] flex items-center gap-[16px] opacity-60">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="h-px flex-1" src={imgDivider} />
          <span className="text-[10px] text-black">or</span>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="h-px flex-1" src={imgDivider} />
        </div>

        <div className="mt-[13px] flex justify-center gap-[21px]">
          <button
            type="button"
            aria-label="Continue with Google"
            className="flex size-10 items-center justify-center rounded-full border border-[#d9d9d9] bg-[#d9d9d980]"
          >
            <GoogleLogo />
          </button>
          <button
            type="button"
            aria-label="Continue with Apple"
            className="flex size-10 items-center justify-center rounded-full border border-[#d9d9d9] bg-[#d9d9d980]"
          >
            <AppleLogo />
          </button>
          <button
            type="button"
            aria-label="Continue with Facebook"
            className="flex size-10 items-center justify-center rounded-full border border-[#d9d9d9] bg-[#d9d9d980]"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-5" src={imgFacebook} />
          </button>
        </div>

        <Link
          href="/profile"
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
