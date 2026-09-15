"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { API_URL } from "@/lib/config";
import { type ExercisePlan, type MovementType } from "@/lib/exercise";
import {
  DEFAULT_READING,
  isCleanRead,
  READING_ROWS,
  type InBodyPayload,
  type SampleExtraction,
} from "@/lib/inbody";
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";
import { ACTIVITY_LABELS, DEFAULT_USER_NAME, type UserProfile } from "@/lib/user";

const imgBack = "/icons/result/back-arrow.svg";
const imgPerson = "/icons/result/person.svg";
const imgGenderMale = "/icons/result/gender-male.svg";
const imgTarget = "/icons/result/target.svg";
const imgDumbbell = "/icons/result/dumbbell.svg";

const MOVEMENT_TYPES: Record<MovementType, { label: string; className: string }> = {
  corrective_unilateral: { label: "Corrective", className: "bg-amber-100 text-amber-900" },
  bilateral_compound: { label: "Compound", className: "bg-[#117d6926] text-[#117d69]" },
  cardio_hiit: { label: "Cardio", className: "bg-sky-100 text-sky-900" },
};

type NutritionTargets = {
  bmr_kcal: number;
  tdee_kcal: number;
  target_calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fats_g: number;
  fiber_g: number;
};

type PlanResponse = {
  nutrition: NutritionTargets;
  exercises: ExercisePlan;
  narrative_text: string;
  narrative_source: "generated" | "fallback";
  corrected_fields?: string[];
};

const NARRATIVE_SOURCES: Record<PlanResponse["narrative_source"], { label: string; note: string }> = {
  generated: {
    label: "Written plan",
    note: "Written by AI around the figures above. The figures themselves are computed, not generated.",
  },
  fallback: {
    label: "Plain plan",
    note: "The written plan couldn't be generated, so this is a plain summary of the same computed figures.",
  },
};

type ApiErrorKind = "network" | "validation";

type State =
  | { status: "loading" }
  | { status: "error"; message: string; kind: ApiErrorKind }
  | { status: "ready"; plan: PlanResponse };

/** FastAPI's `detail` is a string, a validation list, or {message, unread, flagged}. */
function describeApiError(detail: unknown, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map(
        (d: { loc?: (string | number)[]; msg?: string }) =>
          `${d.loc?.[d.loc.length - 1] ?? "value"}: ${d.msg ?? "invalid"}`,
      )
      .join("\n");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return `API returned ${status}`;
}

// The narrative may carry light markdown (the fallback plan always does);
// show it as plain lines rather than raw asterisks and hashes.
function NarrativeText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => {
        const plain = line.replace(/\*\*/g, "").trim();
        if (!plain) return null;
        const heading = plain.match(/^#+\s*(.*)$/);
        return heading ? (
          <p key={i} className="pt-2 font-bold first:pt-0">
            {heading[1]}
          </p>
        ) : (
          <p key={i}>{plain}</p>
        );
      })}
    </>
  );
}

export default function Result() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [reading, setReading] = useState<InBodyPayload | null>(null);
  const [sampleId, setSampleId] = useState<string | null>(null);
  const [corrections, setCorrections] = useState<Record<string, unknown>>({});
  const [fromSample, setFromSample] = useState(true);
  const [name, setName] = useState(DEFAULT_USER_NAME);
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    // Never plan on invented numbers: without a reading there is nothing to compute.
    const loadedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);
    if (!loadedReading) {
      router.replace("/upload");
      return;
    }
    const loadedProfile = loadJSON<UserProfile>(SESSION_KEYS.profile);
    if (!loadedProfile) {
      // A guest picked or confirmed a sheet without a Profile: collect it, then come back.
      saveJSON(SESSION_KEYS.nextAfterProfile, "/result");
      router.replace("/profile");
      return;
    }
    const loadedSampleId = loadJSON<string>(SESSION_KEYS.sampleId);
    const loadedExtraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);
    const loadedCorrections = loadJSON<Record<string, unknown>>(SESSION_KEYS.corrections) ?? {};
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProfile(loadedProfile);
    setReading(loadedReading);
    setSampleId(loadedSampleId);
    setCorrections(loadedCorrections);
    setName(loadJSON<string>(SESSION_KEYS.name) ?? DEFAULT_USER_NAME);

    const hasCorrections = Object.keys(loadedCorrections).length > 0;

    // A clean stored read is planned server-side from the Sample sheet
    // itself; a reading someone edited is sent as they typed it.
    const plannedFromSample =
      loadedSampleId !== null &&
      loadedExtraction !== null &&
      isCleanRead(loadedExtraction) &&
      !hasCorrections &&
      JSON.stringify(loadedExtraction.data) === JSON.stringify(loadedReading);
    setFromSample(plannedFromSample);

    const requestBody = plannedFromSample
      ? { user: loadedProfile, sample_id: loadedSampleId }
      : loadedSampleId
        ? {
            user: loadedProfile,
            sample_id: loadedSampleId,
            ...(hasCorrections ? { corrections: loadedCorrections } : {}),
          }
        : {
            user: loadedProfile,
            inbody: loadedReading,
            ...(hasCorrections ? { corrections: loadedCorrections } : {}),
          };

    fetch(`${API_URL}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    })
      .then(async (res) => {
        if (!res.ok) {
          // A 4xx here means the request itself was rejected (e.g. a typed
          // value out of range) — a different problem from not reaching the
          // API at all, and worth telling apart in the UI.
          const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
          const kind: ApiErrorKind =
            res.status >= 400 && res.status < 500 ? "validation" : "network";
          const error = new Error(describeApiError(body?.detail, res.status));
          Object.assign(error, { kind });
          throw error;
        }
        const plan = (await res.json()) as PlanResponse;
        setState({ status: "ready", plan });
      })
      .catch((err: Error & { kind?: ApiErrorKind }) => {
        setState({ status: "error", message: err.message, kind: err.kind ?? "network" });
      });
  }, [router]);

  const isDemoReading =
    !fromSample && reading !== null && JSON.stringify(reading) === JSON.stringify(DEFAULT_READING);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="flex items-center gap-3 px-[30px] pt-[62px]">
        <Link
          href={fromSample ? "/upload" : "/preview"}
          className="flex size-8 items-center justify-center rounded-full bg-white shadow-md"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="Back" className="size-[18px]" src={imgBack} />
        </Link>
        <h1 className="text-[24px] font-bold text-[#fcfcfc]">Result</h1>
      </div>

      {profile && (
        <div className="mx-[24px] mt-[31px] grid grid-cols-2 gap-x-4 gap-y-3 rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-black">
          <div className="flex items-center gap-2 text-[13px] font-bold">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-4" src={imgPerson} />
            {name}
          </div>
          <div className="flex items-center gap-2 text-[13px] font-bold capitalize">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-4" src={imgTarget} />
            {profile.fitness_goal.replace("_", " ")}
          </div>
          <div className="flex items-center gap-2 text-[13px] font-bold capitalize">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-4" src={imgGenderMale} />
            {profile.biological_sex}
          </div>
          <div className="flex items-center gap-2 text-[13px] font-bold">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-4" src={imgDumbbell} />
            {ACTIVITY_LABELS[profile.activity_multiplier] ?? `${profile.activity_multiplier}x`}
          </div>
        </div>
      )}

      {isDemoReading && (
        <p className="mx-[24px] mt-2 text-[10px] text-white/70">
          Computed from the demo baseline values, not a reading of your sheet.
        </p>
      )}

      {/* Screen 4: the extracted numbers beside the sheet they came from */}
      {profile && reading && (
        <section className="mx-[24px] mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[14px] text-black">
          <h2 className="text-[13px] font-bold">
            {fromSample ? "Read from your sheet" : "Your values, including any you edited"}
          </h2>
          <div className="mt-2 grid grid-cols-[110px_1fr] gap-3">
            {sampleId ? (
              <a
                href={`${API_URL}/samples/${sampleId}/image`}
                target="_blank"
                rel="noreferrer"
                className="block h-[210px] overflow-hidden rounded-lg bg-[#1f1f1f]"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt="The InBody sheet these values were read from"
                  className="size-full object-contain object-top"
                  src={`${API_URL}/samples/${sampleId}/image`}
                />
              </a>
            ) : (
              <div className="h-[210px] overflow-hidden rounded-lg bg-[#1f1f1f]">
                <ReportPhoto emptyLabel="Photos aren't kept after you confirm" />
              </div>
            )}
            <dl className="text-[10px]">
              {(() => {
                const correctedSet = new Set<string>([
                  ...(state.status === "ready" && state.plan.corrected_fields
                    ? state.plan.corrected_fields
                    : []),
                  ...Object.keys(corrections),
                ]);
                return READING_ROWS.map((row) => {
                  const isHumanSupplied =
                    correctedSet.has(row.key) ||
                    correctedSet.has(row.key.replace("segmental_lean.", ""));
                  return (
                    <div
                      key={row.label}
                      className="flex items-baseline justify-between gap-2 border-b border-black/5 py-[3px] last:border-0"
                    >
                      <dt className="flex items-center gap-1.5">
                        <span className="opacity-70">{row.label}</span>
                        {isHumanSupplied && (
                          <span className="rounded bg-sky-100 px-1 py-0.5 text-[8px] font-bold text-sky-800">
                            Human-supplied
                          </span>
                        )}
                      </dt>
                      <dd className="whitespace-nowrap font-bold">
                        {row.value(reading) ?? "—"}{" "}
                        <span className="text-[8px] font-medium opacity-60">{row.unit}</span>
                      </dd>
                    </div>
                  );
                });
              })()}
            </dl>
          </div>
        </section>
      )}

      {state.status === "loading" && (
        <div className="mx-[24px] mt-[15px] flex h-[120px] items-center justify-center rounded-[15px] border-[3px] border-[#f5f5f5] bg-white">
          <p className="text-[12px] text-black/50">Computing your plan…</p>
        </div>
      )}

      {state.status === "error" && state.kind === "validation" && (
        <div className="mx-[24px] mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-center text-[12px] text-black">
          <p className="font-bold text-red-600">The API rejected one of the values</p>
          <p className="mt-1 whitespace-pre-wrap opacity-70">{state.message}</p>
          <p className="mt-2 opacity-70">Go back and check the edited fields.</p>
        </div>
      )}

      {state.status === "error" && state.kind === "network" && (
        <div className="mx-[24px] mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-center text-[12px] text-black">
          <p className="font-bold text-red-600">Couldn&apos;t reach the API</p>
          <p className="mt-1 opacity-70">{state.message}</p>
          <p className="mt-2 opacity-70">
            Is the backend running at <code>{API_URL}</code>?
          </p>
        </div>
      )}

      {state.status === "ready" && (
        <>
          {/* Screen 5: nutrition */}
          <div className="mx-[24px] mt-[15px] flex flex-col items-center rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-black">
            <p className="text-[11px] opacity-60">Daily Energy Target</p>
            <p className="text-[32px] font-bold text-[#117d69]">
              {Math.round(state.plan.nutrition.target_calories_kcal)}
            </p>
            <p className="text-[11px] opacity-60">kcal</p>
            <p className="mt-2 text-[10px] opacity-70">
              BMR {Math.round(state.plan.nutrition.bmr_kcal)} kcal · TDEE{" "}
              {Math.round(state.plan.nutrition.tdee_kcal)} kcal
            </p>
          </div>

          <div className="mx-[24px] mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-black">
            <p className="text-[13px] font-bold">Macros</p>
            <div className="mt-2 grid grid-cols-4 gap-2 text-center">
              {(
                [
                  ["Protein", state.plan.nutrition.protein_g],
                  ["Carbs", state.plan.nutrition.carbs_g],
                  ["Fats", state.plan.nutrition.fats_g],
                  ["Fiber", state.plan.nutrition.fiber_g],
                ] as const
              ).map(([label, grams]) => (
                <div key={label}>
                  <p className="text-[14px] font-bold text-[#117d69]">{Math.round(grams)}g</p>
                  <p className="text-[9px] opacity-60">{label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Screen 6: imbalances */}
          <div className="mx-[24px] mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-black">
            <p className="text-[13px] font-bold">Left/right balance</p>
            {state.plan.exercises.detected_imbalances.length === 0 ? (
              <p className="mt-1 text-[11px] text-[#117d69]">
                Your left and right sides are within 5% of each other. No imbalance to correct.
              </p>
            ) : (
              state.plan.exercises.detected_imbalances.map((imbalance) => (
                <p key={imbalance} className="mt-1 text-[11px]">
                  {imbalance}
                </p>
              ))
            )}
          </div>

          {/* Screen 7: exercises */}
          <div className="mx-[24px] mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-black">
            <p className="text-[13px] font-bold">Recommended Workout</p>
            <ul className="mt-2 space-y-2">
              {state.plan.exercises.exercises.map((ex) => {
                const type = MOVEMENT_TYPES[ex.movement_type];
                return (
                  <li key={ex.name} className="border-b border-black/5 pb-2 text-[11px] last:border-0">
                    <span className="font-bold">{ex.name}</span>
                    <span className={`ml-1 rounded px-1.5 py-0.5 text-[8px] font-bold ${type.className}`}>
                      {type.label}
                    </span>
                    <span className="block text-[10px] opacity-60">Target muscle: {ex.target}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* The narrative, set apart from the audited number blocks above */}
          <section className="mx-[24px] mb-6 mt-[15px] rounded-[15px] border-l-4 border-[#2dd4bf] bg-[#2a2a2a] p-[18px] text-[#fcfcfc]">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[#2dd4bf]">
              {NARRATIVE_SOURCES[state.plan.narrative_source].label}
            </p>
            <p className="mt-1 text-[10px] text-white/60">
              {NARRATIVE_SOURCES[state.plan.narrative_source].note}
            </p>
            <div className="mt-3 space-y-1 font-serif text-[13px] leading-relaxed">
              <NarrativeText text={state.plan.narrative_text} />
            </div>
          </section>
        </>
      )}
    </PhoneFrame>
  );
}
