"use client";

import { useEffect, useState } from "react";
import { loadJSON, SESSION_KEYS } from "@/lib/session";

/** Shows the photo from the Upload flow. Confirming the reading drops the
 * photo from session storage (ADR-0011 §3), so screens after Confirm pass an
 * `emptyLabel` that says so. */
export default function ReportPhoto({
  className = "",
  emptyLabel = "No photo uploaded",
}: {
  className?: string;
  emptyLabel?: string;
}) {
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
      className={`flex size-full flex-col items-center justify-center p-4 text-center ${className}`}
    >
      <span className="text-[12px] font-semibold text-white/80">InBody Scan</span>
      <span className="mt-1 text-[9px] text-white/50">{emptyLabel}</span>
    </div>
  );
}
