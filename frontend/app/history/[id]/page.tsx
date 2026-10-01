"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import { NarrativeProvenance, NarrativeText } from "@/components/Narrative";
import PhoneFrame from "@/components/PhoneFrame";
import { cardClass, Tag } from "@/components/ui";
import { useAuth } from "@/lib/AuthProvider";
import { ApiError } from "@/lib/api";
import { type MovementType } from "@/lib/exercise";
import { READING_ROWS } from "@/lib/inbody";
import { getScan, type ScanDetail } from "@/lib/scans";

const MOVEMENT_TYPES: Record<MovementType, string> = {
  corrective_unilateral: "Corrective Unilateral",
  bilateral_compound: "Compound",
  cardio_hiit: "Cardio HIIT",
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; scan: ScanDetail };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });
}

const fmt = (n: number) => Math.round(n).toLocaleString("en-US");

export default function ScanDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { account, loading: authLoading } = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    if (authLoading) return;
    if (!account) {
      router.replace("/sign-in");
      return;
    }
    getScan(params.id)
      .then((scan) => setState({ status: "ready", scan }))
      .catch((err: unknown) => {
        const message =
          err instanceof ApiError && err.status === 404
            ? "This scan couldn't be found."
            : "Couldn't load this scan.";
        setState({ status: "error", message });
      });
  }, [account, authLoading, params.id, router]);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]" scrollable>
      <header className="flex h-[120px] items-start justify-between bg-gradient-to-b from-black/60 to-transparent px-[30px] pt-[60px]">
        <BackButton href="/history" label="Back to history" />
        <h1 className="text-[20px] font-bold tracking-[0.02em] text-[#fcfcfc]">
          {state.status === "ready" ? formatDate(state.scan.created_at) : "Scan"}
        </h1>
      </header>

      <div className="space-y-[15px] px-[30px] pb-[40px] pt-[20px]">
        {(authLoading || state.status === "loading") && (
          <p role="status" className="text-center text-[12px] text-white/60">
            Loading this scan…
          </p>
        )}

        {state.status === "error" && (
          <div role="alert" className={`${cardClass} p-[18px] text-center text-[12px] font-bold text-rose-700`}>
            {state.message}
          </div>
        )}

        {state.status === "ready" && (
          <>
            <section className={`${cardClass} p-[20px]`}>
              <h2 className="text-[10px] font-bold">Reading, as used for this plan</h2>
              <dl className="mt-[10px] text-[11px]">
                {READING_ROWS.map((row) => {
                  const short = row.key.replace("segmental_lean.", "");
                  const corrected = new Set(state.scan.corrected_fields);
                  const confirmed = new Set(state.scan.confirmed_fields);
                  const edited = corrected.has(row.key) || corrected.has(short);
                  const checked = !edited && (confirmed.has(row.key) || confirmed.has(short));
                  return (
                    <div key={row.label} className="flex items-baseline justify-between gap-2 border-b border-black/5 py-[3px] last:border-0">
                      <dt className="flex items-center gap-1.5">
                        <span className="text-black/75">{row.label}</span>
                        {edited && <Tag tone="sky">Edited</Tag>}
                        {checked && <Tag tone="teal">Checked</Tag>}
                      </dt>
                      <dd className="whitespace-nowrap font-bold">
                        {row.value(state.scan.effective_inbody) ?? "—"}
                        <span className="ml-[2px] text-[8px] font-medium opacity-60">{row.unit}</span>
                      </dd>
                    </div>
                  );
                })}
              </dl>
            </section>

            <div className="grid grid-cols-2 gap-[15px]">
              <div className={`${cardClass} p-[20px] text-center`}>
                <p className="text-[10px] font-bold">Daily Energy Target</p>
                <p className="mt-[8px] text-[24px] font-bold leading-none text-[#117d69]">
                  {fmt(state.scan.nutrition.target_calories_kcal)}
                </p>
                <p className="mt-[2px] text-[8px] text-black/60">kilocalories / day</p>
                <p className="mt-[10px] text-[8px] text-black/70">
                  BMR {fmt(state.scan.nutrition.bmr_kcal)} · TDEE {fmt(state.scan.nutrition.tdee_kcal)} kcal
                </p>
              </div>
              <div className={`${cardClass} p-[20px]`}>
                <p className="text-[10px] font-bold">Macros</p>
                <dl className="mt-[10px] space-y-[6px] text-[9px]">
                  {(
                    [
                      ["Protein", state.scan.nutrition.protein_g],
                      ["Carbohydrates", state.scan.nutrition.carbs_g],
                      ["Fats", state.scan.nutrition.fats_g],
                      ["Fiber", state.scan.nutrition.fiber_g],
                    ] as const
                  ).map(([label, grams]) => (
                    <div key={label} className="flex items-center justify-between">
                      <dt>{label}</dt>
                      <dd>
                        <strong className="text-[13px] text-[#117d69]">{fmt(grams)}</strong> g
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>

            <section className={`${cardClass} p-[20px]`}>
              <h2 className="text-[10px] font-bold">Left / Right Balance</h2>
              {state.scan.exercises.detected_imbalances.length === 0 ? (
                <p className="mt-[8px] text-[11px] text-[#0b5e4f]">
                  Your left and right sides were within 5% of each other at this scan.
                </p>
              ) : (
                <ul className="mt-[8px] list-disc pl-4 text-[11px]">
                  {state.scan.exercises.detected_imbalances.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ul>
              )}
            </section>

            <section className={`${cardClass} p-[20px]`}>
              <h2 className="text-[10px] font-bold">Recommended Workout</h2>
              <ul className="mt-[12px] space-y-[8px]">
                {state.scan.exercises.exercises.map((ex) => (
                  <li key={ex.name} className="rounded-[8px] border border-[#d9d9d9] px-[15px] py-[9px]">
                    <p className="flex flex-wrap items-center gap-[8px] text-[12px] font-bold">
                      {ex.name}
                      <span className="rounded-[4px] bg-[#117d69]/20 px-[5px] py-[2px] text-[8px] font-bold text-[#0b5e4f]">
                        {MOVEMENT_TYPES[ex.movement_type]}
                      </span>
                    </p>
                    <p className="text-[10px] text-black/70">
                      Target: {ex.target}
                      {ex.equipment ? ` (${ex.equipment})` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            </section>

            {/* A saved Scan froze whether the AI wrote this or it's the plain fallback. */}
            <section className="rounded-[15px] border-l-4 border-[#2dd4bf] bg-black/25 p-[20px] text-[#fcfcfc]">
              <NarrativeProvenance source={state.scan.narrative_source} />
              <div className="mt-3 space-y-2 text-[12px] leading-relaxed text-[#fcfcfc]/90">
                <NarrativeText text={state.scan.narrative_text} />
              </div>
            </section>
          </>
        )}
      </div>
    </PhoneFrame>
  );
}
