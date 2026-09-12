"use client";

import { useEffect, useState } from "react";
import { loadJSON } from "@/lib/session";
import { SESSION_KEYS } from "@/lib/inbody";

/** Shows the photo captured/uploaded in the Upload flow, or a placeholder if
 * none was saved this session (e.g. landed on this screen directly). */
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
      <img alt="Your uploaded report" className={`size-full object-cover ${className}`} src={photo} />
    );
  }

  return (
    <p className={`flex size-full items-center justify-center px-3 text-center text-[12px] text-white/40 ${className}`}>
      Your report photo
    </p>
  );
}
