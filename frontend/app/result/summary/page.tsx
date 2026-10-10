"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import BackButton from "@/components/BackButton";
import {
  NarrativeProvenance,
  NarrativeText,
  type NarrativeSource,
} from "@/components/Narrative";
import PhoneFrame from "@/components/PhoneFrame";
import { loadJSON, SESSION_KEYS } from "@/lib/session";

/** What Result hands over when its plan resolves. */
type StoredNarrative = {
  text: string;
  source: NarrativeSource;
};

/**
 * The written plan, on its own screen.
 *
 * Split off the Result page so the figures lead there and long prose doesn't
 * push them off the top (Requirements 5.1-5.3). A route rather than a modal:
 * prose scrolls badly in a modal on a 402px frame, and a route gets the global
 * Back control for free.
 *
 * Read from the session rather than refetched. The narrative belongs to the plan
 * that was already computed, and asking for it again would mean recomputing the
 * plan — and paying for a second LLM call where one is configured.
 */
export default function ResultSummary() {
  const [narrative, setNarrative] = useState<StoredNarrative | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    /* eslint-disable react-hooks/set-state-in-effect */
    setNarrative(loadJSON<StoredNarrative>(SESSION_KEYS.narrative));
    setLoaded(true);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="flex items-start gap-3 px-[30px] pt-[48px]">
        <BackButton href="/result" label="Back to your results" />
        <h1 className="text-[24px] font-bold text-[#fcfcfc]">Your plan, in words</h1>
      </div>

      {!loaded ? (
        <div className="mx-[24px] mt-[24px] flex h-[120px] items-center justify-center rounded-[15px] bg-[#2a2a2a]">
          <p className="text-[12px] text-white/50">Loading…</p>
        </div>
      ) : narrative ? (
        <>
          <section className="mx-[24px] mb-8 mt-[24px] rounded-[15px] border-l-4 border-[#2dd4bf] bg-[#2a2a2a] p-[18px] text-[#fcfcfc]">
            <NarrativeProvenance source={narrative.source} />
            <div className="mt-4 space-y-2 font-serif text-[14px] leading-relaxed">
              <NarrativeText text={narrative.text} />
            </div>
          </section>

          <p className="mx-[24px] mb-10 text-[10px] leading-relaxed text-white/50">
            General fitness information, not medical advice. Your targets come from published
            formulas applied to your measurements, and take no account of any medical condition.
          </p>
        </>
      ) : (
        <div className="mx-[24px] mt-[24px] rounded-[15px] bg-white p-[25px] text-center text-black">
          <p className="text-[13px] font-bold">Nothing to show yet</p>
          <p className="mt-2 text-[12px] text-zinc-600">
            The written plan is put together alongside your results, so it needs a plan to exist
            first.
          </p>
          <Link
            href="/result"
            className="mt-4 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white shadow-sm"
          >
            Go to your results
          </Link>
        </div>
      )}
    </PhoneFrame>
  );
}
