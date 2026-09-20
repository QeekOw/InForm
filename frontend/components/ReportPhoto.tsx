"use client";

import { useEffect, useState } from "react";
import { pagesReadNotice } from "@/lib/photo";
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
  const [pagesNotice, setPagesNotice] = useState<string | null>(null);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPhoto(loadJSON<string>(SESSION_KEYS.photo));
    setPagesNotice(pagesReadNotice(loadJSON<number>(SESSION_KEYS.sheetPages) ?? 1));
  }, []);

  if (photo) {
    return (
      <div className={`relative size-full ${className}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="Your uploaded report" className="size-full object-cover" src={photo} />
        {/* A multi-page PDF only ever has page 1 read, so say so next to the
            page the numbers were taken from (issue #81). */}
        {pagesNotice && (
          <span className="absolute inset-x-0 bottom-0 bg-black/70 px-2 py-1 text-center text-[9px] font-medium text-white/90">
            {pagesNotice}
          </span>
        )}
      </div>
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
