"use client";

import { useEffect, useState } from "react";
import { loadJSON } from "@/lib/session";
import { SESSION_KEYS } from "@/lib/inbody";

/** Shows the photo captured/uploaded in the Upload flow during review.
 * Per ADR-0011 §3, when the user confirms their scan, the photo is cleared
 * from session storage, and this component renders a privacy badge confirming
 * Zero Image Persistence. */
export default function ReportPhoto({ className = "" }: { className?: string }) {
  const [photo, setPhoto] = useState<string | null>(null);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPhoto(loadJSON<string>(SESSION_KEYS.photo));
  }, []);

  if (photo) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        alt="Your uploaded report"
        className={`size-full object-cover ${className}`}
        src={photo}
      />
    );
  }

  return (
    <div
      className={`flex size-full flex-col items-center justify-center p-4 text-center text-white/50 ${className}`}
    >
      <span className="text-[12px] font-semibold text-white/80">InBody Scan</span>
      <span className="mt-1 text-[9px] text-white/40">
        Photo cleared per ADR-0011 (Zero Image Persistence)
      </span>
    </div>
  );
}
