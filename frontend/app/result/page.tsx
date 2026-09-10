"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PhoneFrame from "@/components/PhoneFrame";
import { loadJSON } from "@/lib/session";
import { DEFAULT_PROFILE, DEFAULT_READING, SESSION_KEYS, type InBodyReading, type UserProfile } from "@/lib/inbody";

const imgBack = "/icons/result/back-arrow.svg";
const imgPerson = "/icons/result/person.svg";
const imgGenderMale = "/icons/result/gender-male.svg";
const imgTarget = "/icons/result/target.svg";
const imgDumbbell = "/icons/result/dumbbell.svg";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ACTIVITY_LABELS: Record<number, string> = {
  1.2: "Sedentary",
  1.375: "Lightly active",
  1.55: "Moderately active",
  1.725: "Very active",
  1.9: "Extremely active",
};

type Exercise = {
  name: string;
  target: string;
  movement_type: string;
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
  exercises: { exercises: Exercise[]; detected_imbalances: string[] };
  narrative_text: string;
};

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; plan: PlanResponse };

export default function Result() {
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [name, setName] = useState("John Doe");
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    const loadedProfile = loadJSON<UserProfile>(SESSION_KEYS.profile) ?? DEFAULT_PROFILE;
    const loadedReading = loadJSON<InBodyReading>(SESSION_KEYS.reading) ?? DEFAULT_READING;
    const loadedName = loadJSON<string>("inform:name") ?? "John Doe";
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setProfile(loadedProfile);
    setName(loadedName);

    fetch(`${API_URL}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: loadedProfile, inbody: loadedReading }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const plan = (await res.json()) as PlanResponse;
        setState({ status: "ready", plan });
      })
      .catch((err: Error) => {
        setState({ status: "error", message: err.message });
      });
  }, []);

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

      {state.status === "loading" && (
        <div className="mx-[24px] mt-[15px] flex h-[217px] items-center justify-center rounded-[15px] border-[3px] border-[#f5f5f5] bg-white">
          <p className="text-[12px] text-black/50">Computing your plan…</p>
        </div>
      )}

      {state.status === "error" && (
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
            <div className="flex h-[217px] items-center justify-center rounded-[15px] bg-[#1f1f1f]">
              <p className="px-3 text-center text-[11px] text-white/40">Your report photo</p>
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
