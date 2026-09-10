"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";

const imgScanLine = "/icons/scan/scan-line.svg";

export default function Analyzing() {
  const router = useRouter();

  useEffect(() => {
    // Stand-in for the real read: Module 1 (Donut) takes ~45s on CPU per the
    // README; this walking-skeleton UI just simulates the wait and moves on.
    const timer = setTimeout(() => router.push("/preview"), 3000);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <h1 className="mx-auto mt-[128px] w-[214px] text-center text-[24px] font-bold text-[#fcfcfc]">
        Analyzing your body composition...
      </h1>

      <div className="relative mx-auto mt-[60px] h-[370px] w-[265px] overflow-hidden rounded-[15px] border-6 border-[#117d69] bg-[#1f1f1f]">
        <p className="absolute inset-0 flex items-center justify-center px-6 text-center text-[12px] text-white/40">
          Reading your report…
        </p>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" className="absolute inset-x-0 w-full animate-scan" src={imgScanLine} />
      </div>
    </PhoneFrame>
  );
}
