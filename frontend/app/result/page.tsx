"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { API_URL } from "@/lib/config";
import { type ExercisePlan } from "@/lib/exercise";
import { DEFAULT_READING, type InBodyPayload } from "@/lib/inbody";
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";
import { ACTIVITY_LABELS, DEFAULT_USER_NAME, type UserProfile } from "@/lib/user";

const imgBack = "/icons/result/back-arrow.svg";
const imgPerson = "/icons/result/person.svg";
const imgGenderMale = "/icons/result/gender-male.svg";
const imgTarget = "/icons/result/target.svg";
const imgDumbbell = "/icons/result/dumbbell.svg";

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
};

type ApiErrorKind = "network" | "validation";

type State =
  | { status: "loading" }
  | { status: "error"; message: string; kind: ApiErrorKind }
  | { status: "ready"; plan: PlanResponse };

/** Turns FastAPI's 422 body into one "field: problem" line per error. */
function describeValidationError(body: string): string {
  try {
    const { detail } = JSON.parse(body) as {
      detail?: { loc?: (string | number)[]; msg?: string }[];
    };
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((d) => `${d.loc?.[d.loc.length - 1] ?? "value"}: ${d.msg ?? "invalid"}`)
        .join("\n");
    }
  } catch {
    // Not JSON: show the body as it came.
  }
  return body;
}

export default function Result() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [name, setName] = useState(DEFAULT_USER_NAME);
  const [isDemoReading, setIsDemoReading] = useState(false);
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const loadedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);
    if (!loadedReading) {
      router.replace("/upload");
      return;
    }
    const loadedProfile = loadJSON<UserProfile>(SESSION_KEYS.profile);
    if (!loadedProfile) {
      // A guest confirmed a reading without a Profile: collect it, then come back.
      saveJSON(SESSION_KEYS.nextAfterProfile, "/result");
      router.replace("/profile");
      return;
    }
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProfile(loadedProfile);
    setName(loadJSON<string>(SESSION_KEYS.name) ?? DEFAULT_USER_NAME);
    setIsDemoReading(JSON.stringify(loadedReading) === JSON.stringify(DEFAULT_READING));

    fetch(`${API_URL}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: loadedProfile, inbody: loadedReading }),
    })
      .then(async (res) => {
        if (!res.ok) {
          // A 4xx here means the request itself was rejected (e.g. a typed
          // value out of range) — a different problem from not reaching the
          // API at all, and worth telling apart in the UI.
          const detail = await res.text().catch(() => "");
          const kind: ApiErrorKind =
            res.status >= 400 && res.status < 500 ? "validation" : "network";
          const message =
            kind === "validation" ? describeValidationError(detail) : detail;
          const error = new Error(message || `API returned ${res.status}`);
          Object.assign(error, { kind });
          throw error;
        }
        const plan = (await res.json()) as PlanResponse;
        setState({ status: "ready", plan });
      })
      .catch((err: Error & { kind?: ApiErrorKind }) => {
        setState({
          status: "error",
          message: err.message,
          kind: err.kind ?? "network",
        });
      });
  }, [router]);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="flex items-center gap-3 px-[30px] pt-[62px]">
        <Link
          href="/preview"
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

      {state.status === "loading" && (
        <div className="mx-[24px] mt-[15px] flex h-[217px] items-center justify-center rounded-[15px] border-[3px] border-[#f5f5f5] bg-white">
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
          <div className="mx-[24px] mt-[15px] grid grid-cols-[157px_1fr] gap-[8px]">
            <div className="h-[217px] overflow-hidden rounded-[15px] bg-[#1f1f1f]">
              <ReportPhoto emptyLabel="Photos aren't kept after you confirm" />
            </div>
            <div className="flex h-[217px] flex-col items-center justify-center rounded-[15px] border-[3px] border-[#f5f5f5] bg-white text-black">
              <p className="text-[11px] opacity-60">Daily Energy Target</p>
              <p className="text-[32px] font-bold text-[#117d69]">
                {Math.round(state.plan.nutrition.target_calories_kcal)}
              </p>
              <p className="text-[11px] opacity-60">kcal</p>
              <div className="mt-3 text-center text-[9px] opacity-70">
                <p>BMR {Math.round(state.plan.nutrition.bmr_kcal)} kcal</p>
                <p>TDEE {Math.round(state.plan.nutrition.tdee_kcal)} kcal</p>
              </div>
            </div>
          </div>

          <div className="mx-[24px] mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-black">
            <p className="text-[13px] font-bold">Macros</p>
            <div className="mt-2 grid grid-cols-4 gap-2 text-center">
              <div>
                <p className="text-[14px] font-bold text-[#117d69]">
                  {Math.round(state.plan.nutrition.protein_g)}g
                </p>
                <p className="text-[9px] opacity-60">Protein</p>
              </div>
              <div>
                <p className="text-[14px] font-bold text-[#117d69]">
                  {Math.round(state.plan.nutrition.carbs_g)}g
                </p>
                <p className="text-[9px] opacity-60">Carbs</p>
              </div>
              <div>
                <p className="text-[14px] font-bold text-[#117d69]">
                  {Math.round(state.plan.nutrition.fats_g)}g
                </p>
                <p className="text-[9px] opacity-60">Fats</p>
              </div>
              <div>
                <p className="text-[14px] font-bold text-[#117d69]">
                  {Math.round(state.plan.nutrition.fiber_g)}g
                </p>
                <p className="text-[9px] opacity-60">Fiber</p>
              </div>
            </div>
          </div>

          <div className="mx-[24px] mb-6 mt-[15px] rounded-[15px] border-[3px] border-[#f5f5f5] bg-white p-[18px] text-black">
            <p className="text-[13px] font-bold">Recommended Workout</p>
            {state.plan.exercises.detected_imbalances.length === 0 ? (
              <p className="mt-1 text-[10px] text-[#117d69]">No asymmetry detected.</p>
            ) : (
              state.plan.exercises.detected_imbalances.map((imbalance) => (
                <p key={imbalance} className="mt-1 text-[10px] text-[#117d69]">
                  ⚠ {imbalance}
                </p>
              ))
            )}
            <ul className="mt-3 space-y-2">
              {state.plan.exercises.exercises.map((ex) => (
                <li key={ex.name} className="border-b border-black/5 pb-2 text-[11px] last:border-0">
                  <span className="font-bold">{ex.name}</span>
                  <span className="ml-1 rounded bg-[#117d6926] px-1.5 py-0.5 text-[8px] text-[#117d69]">
                    {ex.movement_type.replace("_", " ")}
                  </span>
                  <span className="block text-[9px] opacity-60">targets {ex.target}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </PhoneFrame>
  );
}
