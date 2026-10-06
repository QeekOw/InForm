"use client";

import { useCallback, useEffect, useRef, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import BackButton from "@/components/BackButton";
import { CheckedMarker, EditedMarker, MarkerLegend } from "@/components/FieldStatus";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, cardClass, ConfirmDialog, Modal } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { API_URL } from "@/lib/config";
import { type ExercisePlan, type MovementType } from "@/lib/exercise";
import {
  DEFAULT_READING,
  isCleanRead,
  READING_ROWS,
  type InBodyPayload,
  type PartialInBody,
  type SampleExtraction,
} from "@/lib/inbody";
import { GOAL_LABELS } from "@/lib/profileOptions";
import {
  computeScanFingerprint,
  listScans,
  saveScan,
  type SaveScanRequest,
  type ScanSummary,
} from "@/lib/scans";
import { clearSheet, loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "@/lib/session";
import { ACTIVITY_LABELS, ageFromDob, DEFAULT_USER_NAME, type UserProfile } from "@/lib/user";

const MOVEMENT_TYPES: Record<MovementType, string> = {
  corrective_unilateral: "Corrective Unilateral",
  bilateral_compound: "Compound",
  cardio_hiit: "Cardio HIIT",
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
  confirmed_fields?: string[];
  measured?: PartialInBody | null;
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

type SaveState = "idle" | "saving" | "saved" | "error";

const fmt = (n: number) => Math.round(n).toLocaleString("en-US");

/** The plan as plain text, for "Copy to clipboard" in the Summary. */
function planAsText(plan: PlanResponse, profile: UserProfile): string {
  const n = plan.nutrition;
  const lines = [
    `Daily Fitness and Nutrition Plan (${GOAL_LABELS[profile.fitness_goal]})`,
    "",
    "Nutritional Targets",
    `Daily Energy Target: ${fmt(n.target_calories_kcal)} kcal`,
    `BMR: ${fmt(n.bmr_kcal)} kcal, TDEE: ${fmt(n.tdee_kcal)} kcal`,
    `Protein: ${fmt(n.protein_g)} g`,
    `Carbohydrates: ${fmt(n.carbs_g)} g`,
    `Fats: ${fmt(n.fats_g)} g`,
    `Fiber: ${fmt(n.fiber_g)} g`,
    "",
    "Recommended Workout Program",
    ...(plan.exercises.detected_imbalances.length > 0
      ? ["Detected imbalances:", ...plan.exercises.detected_imbalances.map((i) => `- ${i}`), ""]
      : []),
    ...plan.exercises.exercises.map(
      (ex) => `- ${ex.name} (${MOVEMENT_TYPES[ex.movement_type]}): targets ${ex.target}${ex.equipment ? `, ${ex.equipment}` : ""}`,
    ),
    "",
    "General fitness information, not medical advice. — InForm",
  ];
  return lines.join("\n");
}

function ResultContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const shouldAutoSave = searchParams.get("save") === "1";
  const { account } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [reading, setReading] = useState<InBodyPayload | null>(null);
  const [sampleId, setSampleId] = useState<string | null>(null);
  const [corrections, setCorrections] = useState<Record<string, unknown>>({});
  const [confirmations, setConfirmations] = useState<string[]>([]);
  const [fromSample, setFromSample] = useState(true);
  const [name, setName] = useState(DEFAULT_USER_NAME);
  const [state, setState] = useState<State>({ status: "loading" });
  const [planRequestBody, setPlanRequestBody] = useState<SaveScanRequest | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [duplicateScan, setDuplicateScan] = useState<ScanSummary | null>(null);
  // Which popup is open, if any.
  const [dialog, setDialog] = useState<
    null | "summary" | "discard" | "saved" | "guestSave" | "duplicate" | "sheet"
  >(null);
  const [copied, setCopied] = useState(false);
  const autoSaveTried = useRef(false);

  useEffect(() => {
    // Never plan on invented numbers: without a reading there is nothing to compute.
    const loadedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);
    if (!loadedReading) {
      router.replace("/upload");
      return;
    }
    let loadedProfile = loadJSON<UserProfile>(SESSION_KEYS.profile);
    if (!loadedProfile && account) {
      if (
        account.date_of_birth &&
        account.default_biological_sex &&
        account.default_activity_multiplier &&
        account.default_fitness_goal
      ) {
        const age = ageFromDob(account.date_of_birth);
        if (age !== null) {
          loadedProfile = {
            age,
            biological_sex: account.default_biological_sex,
            activity_multiplier: account.default_activity_multiplier,
            fitness_goal: account.default_fitness_goal,
          };
          saveJSON(SESSION_KEYS.profile, loadedProfile);
        }
      }
    }
    if (!loadedProfile) {
      // A guest picked or confirmed a sheet without a Profile: collect it, then come back.
      saveJSON(SESSION_KEYS.nextAfterProfile, "/result");
      router.replace("/profile");
      return;
    }
    const loadedSampleId = loadJSON<string>(SESSION_KEYS.sampleId);
    const loadedReadId = loadJSON<string>(SESSION_KEYS.readId);
    const loadedExtraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);
    const loadedCorrections = loadJSON<Record<string, unknown>>(SESSION_KEYS.corrections) ?? {};
    const loadedConfirmations = loadJSON<string[]>(SESSION_KEYS.confirmations) ?? [];
    const loadedMeasured =
      loadJSON<PartialInBody>(SESSION_KEYS.measured) ?? loadedExtraction?.data;
    // sessionStorage is a browser-only external store, unreadable during SSR.
    /* eslint-disable react-hooks/set-state-in-effect */
    setProfile(loadedProfile);
    setReading(loadedReading);
    setSampleId(loadedSampleId);
    setCorrections(loadedCorrections);
    setConfirmations(loadedConfirmations);
    setName(loadJSON<string>(SESSION_KEYS.name) ?? DEFAULT_USER_NAME);
    /* eslint-enable react-hooks/set-state-in-effect */

    // ADR-0011: the photo is never kept once a plan has been built from it.
    removeSessionItem(SESSION_KEYS.photo);

    const hasCorrections = Object.keys(loadedCorrections).length > 0;
    const hasConfirmations = loadedConfirmations.length > 0;

    // A clean stored read is planned server-side from the Sample sheet
    // itself; a reading someone edited or confirmed is sent as they verified/typed it.
    const plannedFromSample =
      loadedSampleId !== null &&
      loadedExtraction !== null &&
      isCleanRead(loadedExtraction) &&
      !hasCorrections &&
      !hasConfirmations &&
      JSON.stringify(loadedExtraction.data) === JSON.stringify(loadedReading);
    setFromSample(plannedFromSample);

    const extras = {
      ...(hasCorrections ? { corrections: loadedCorrections } : {}),
      ...(hasConfirmations ? { confirmations: loadedConfirmations } : {}),
    };
    const flaggedExtra = loadedExtraction?.flagged?.length
      ? { initial_flagged: loadedExtraction.flagged }
      : {};
    const requestBody: SaveScanRequest = loadedReadId
      ? { user: loadedProfile, read_id: loadedReadId, ...extras }
      : loadedSampleId
        ? { user: loadedProfile, sample_id: loadedSampleId, ...extras }
        : loadedMeasured
          ? { user: loadedProfile, measured: loadedMeasured, ...extras, ...flaggedExtra }
          : { user: loadedProfile, inbody: loadedReading, ...extras, ...flaggedExtra };

    // Kept so Save sends exactly what produced these results.
    setPlanRequestBody(requestBody);

    fetch(`${API_URL}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
          const kind: ApiErrorKind = res.status >= 400 && res.status < 500 ? "validation" : "network";
          const error = new Error(describeApiError(body?.detail, res.status));
          Object.assign(error, { kind });
          throw error;
        }
        const plan = (await res.json()) as PlanResponse;
        // Also readable on /result/summary without recomputing the plan.
        saveJSON(SESSION_KEYS.narrative, { text: plan.narrative_text, source: plan.narrative_source });
        setState({ status: "ready", plan });
      })
      .catch((err: Error & { kind?: ApiErrorKind }) => {
        setState({ status: "error", message: err.message, kind: err.kind ?? "network" });
      });
    // Runs once per visit; `account` is read for a pre-fill fallback only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  const isDemoReading =
    !fromSample && reading !== null && JSON.stringify(reading) === JSON.stringify(DEFAULT_READING);

  /** Drop the in-progress reading without saving. A Scan already saved is untouched. */
  const handleDiscard = () => {
    clearSheet();
    router.push(account ? "/dashboard" : "/upload");
  };

  const doSave = useCallback(async () => {
    if (!planRequestBody) return;
    setSaveState("saving");
    setSaveError(null);
    try {
      await saveScan(planRequestBody);
      setSaveState("saved");
      setDuplicateScan(null);
      setDialog("saved");
    } catch (err) {
      setSaveState("error");
      setSaveError(err instanceof ApiError ? String(err.message) : "Couldn't save this scan. Try again.");
    }
  }, [planRequestBody]);

  /** Save: guests are asked to sign in; signed-in people get a duplicate check first. */
  const handleSave = useCallback(async () => {
    if (!account) {
      setDialog("guestSave");
      return;
    }
    if (saveState === "saved") {
      setDialog("saved");
      return;
    }
    const currentFingerprint = computeScanFingerprint({
      sampleId,
      weight_kg: reading?.weight_kg,
      skeletal_muscle_mass_kg: reading?.skeletal_muscle_mass_kg,
      percent_body_fat: reading?.percent_body_fat,
      lean_body_mass_kg: reading?.lean_body_mass_kg,
      source_device: reading?.source_device,
    });
    setSaveState("saving");
    try {
      const scans = await listScans();
      const match = scans.find((s) => {
        if (s.scan_fingerprint && s.scan_fingerprint === currentFingerprint) return true;
        return (
          computeScanFingerprint({
            sampleId: s.sample_id,
            weight_kg: s.weight_kg,
            skeletal_muscle_mass_kg: s.skeletal_muscle_mass_kg,
            percent_body_fat: s.percent_body_fat,
            lean_body_mass_kg: s.lean_body_mass_kg,
          }) === currentFingerprint
        );
      });
      if (match) {
        setSaveState("idle");
        setDuplicateScan(match);
        setDialog("duplicate");
        return;
      }
    } catch (err) {
      // The duplicate check is a courtesy; failing it shouldn't block saving.
      console.error("Failed to check duplicate scans:", err);
    }
    await doSave();
  }, [account, saveState, sampleId, reading, doSave]);

  // Coming back from sign-in/sign-up with ?save=1 finishes the save they asked for.
  useEffect(() => {
    if (!shouldAutoSave || !account || state.status !== "ready" || !planRequestBody) return;
    if (autoSaveTried.current) return;
    autoSaveTried.current = true;
    void handleSave();
  }, [shouldAutoSave, account, state.status, planRequestBody, handleSave]);

  const handleCopy = async () => {
    if (state.status !== "ready" || !profile) return;
    try {
      await navigator.clipboard.writeText(planAsText(state.plan, profile));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const correctedSet = new Set<string>([
    ...(state.status === "ready" ? state.plan.corrected_fields ?? [] : []),
    ...Object.keys(corrections),
  ]);
  const confirmedSet = new Set<string>([
    ...(state.status === "ready" ? state.plan.confirmed_fields ?? [] : []),
    ...confirmations,
  ]);
  const sheetImage = sampleId ? `${API_URL}/samples/${sampleId}/image` : null;

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      {/* Header photo */}
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[218px] overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="" src="/bg/result.jpg" className="size-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-[#3e3e3e]/50 to-[#3e3e3e]" />
      </div>

      <div className="relative px-[30px] pb-[48px] pt-[48px] text-[#fcfcfc]">
        <BackButton href="/preview" label="Back to reading preview" />
        <h1 className="mt-[57px] text-[24px] font-bold tracking-[0.02em]">Your InBody Results</h1>

        {profile && (
          <div className={`${cardClass} mt-[20px] grid grid-cols-2 gap-x-[20px] gap-y-[10px] px-[20px] py-[20px] text-[12px] font-bold`}>
            <span className="flex items-center gap-[10px]">
              <Icon name="person" size={16} />
              <span className="truncate">{name}</span>
            </span>
            <span className="flex items-center gap-[10px]">
              <Icon name="scale" size={16} />
              {GOAL_LABELS[profile.fitness_goal]}
            </span>
            <span className="flex items-center gap-[10px]">
              <Icon name={profile.biological_sex === "female" ? "genderFemale" : "genderMale"} size={16} />
              {profile.biological_sex === "female" ? "Female" : "Male"}
            </span>
            <span className="flex items-center gap-[10px]">
              <Icon name="target" size={16} />
              {ACTIVITY_LABELS[profile.activity_multiplier] ?? `${profile.activity_multiplier}x`}
            </span>
          </div>
        )}

        {isDemoReading && (
          <p className="mt-2 text-[10px] text-white/70">
            Computed from the demo baseline values, not a reading of your sheet.
          </p>
        )}

        {/* The numbers beside the sheet they came from */}
        {profile && reading && (
          <section aria-label="Your readings" className="mt-[20px] grid grid-cols-[164px_1fr] gap-[15px]">
            <div className="relative h-[227px] overflow-hidden rounded-[15px] bg-[#1f1f1f]">
              {sheetImage ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img alt="" src={sheetImage} className="size-full object-cover object-top" />
                  <button
                    type="button"
                    onClick={() => setDialog("sheet")}
                    aria-label="View the full sheet"
                    className="absolute right-[15px] top-[15px] flex size-[24px] items-center justify-center rounded-full bg-[#117d69] text-white shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
                  >
                    <Icon name="eye" size={14} />
                  </button>
                </>
              ) : (
                <div className="flex size-full flex-col items-center justify-center gap-2 p-3 text-center text-[10px] text-white/60">
                  <Icon name="image" size={24} />
                  Your photo isn&apos;t kept once your plan is built.
                </div>
              )}
            </div>
            <dl className="text-[11px]">
              {READING_ROWS.map((row) => {
                const short = row.key.replace("segmental_lean.", "");
                const edited = correctedSet.has(row.key) || correctedSet.has(short);
                const checked = !edited && (confirmedSet.has(row.key) || confirmedSet.has(short));
                return (
                  <div key={row.label} className="flex items-baseline justify-between gap-1 py-[2px]">
                    <dt className="flex min-w-0 items-center gap-[4px]">
                      <span className="truncate">{row.label}</span>
                      {edited && <EditedMarker />}
                      {checked && <CheckedMarker />}
                    </dt>
                    <dd className="whitespace-nowrap font-bold">
                      {row.value(reading) ?? "—"}
                      <span className="ml-[2px] text-[8px] font-medium opacity-70">{row.unit}</span>
                    </dd>
                  </div>
                );
              })}

            </dl>
          </section>
        )}
        {profile && reading && <MarkerLegend edited={correctedSet.size > 0} checked={confirmedSet.size > 0} />}

        {state.status === "loading" && (
          <div className={`${cardClass} mt-[15px] flex h-[120px] items-center justify-center`} role="status">
            <p className="text-[12px] text-black/50">Building your plan…</p>
          </div>
        )}

        {state.status === "error" && (
          <div className={`${cardClass} mt-[15px] p-[18px] text-center text-[12px]`} role="alert">
            <p className="font-bold text-rose-700">
              {state.kind === "validation" ? "One of the values was rejected" : "Couldn't reach the server"}
            </p>
            <p className="mt-1 whitespace-pre-wrap text-black/70">{state.message}</p>
            {state.kind === "validation" ? (
              <Link href="/preview/edit" className={`${btn.primary} mt-3`}>
                Check the values
              </Link>
            ) : (
              <button type="button" onClick={() => router.refresh()} className={`${btn.primary} mt-3`}>
                Try again
              </button>
            )}
          </div>
        )}

        {state.status === "ready" && profile && (
          <>
            <div className="mt-[15px] grid grid-cols-2 gap-[15px]">
              {/* Energy */}
              <div className={`${cardClass} flex flex-col p-[20px]`}>
                <p className="text-center text-[10px] font-bold">Daily Energy Target</p>
                <p className="mt-[8px] text-center text-[24px] font-bold leading-none text-[#117d69]">
                  {fmt(state.plan.nutrition.target_calories_kcal)}
                </p>
                <p className="mt-[2px] text-center text-[8px] text-black/60">kilocalories / day</p>
                <div className="my-[14px] h-px bg-black/15" />
                <div className="space-y-[4px] text-[8px]">
                  <p className="flex justify-between">
                    <span>BMR Basis</span>
                    <span>
                      <strong className="text-[9px]">{fmt(state.plan.nutrition.bmr_kcal)}</strong> kcal
                    </span>
                  </p>
                  <p className="flex justify-between">
                    <span>TDEE</span>
                    <span>
                      <strong className="text-[9px]">{fmt(state.plan.nutrition.tdee_kcal)}</strong> kcal
                    </span>
                  </p>
                </div>
              </div>

              {/* Macros */}
              <div className={`${cardClass} p-[20px]`}>
                <p className="text-[10px] font-bold">Macros</p>
                <dl className="mt-[12px] space-y-[8px] text-[9px]">
                  {(
                    [
                      ["Protein", state.plan.nutrition.protein_g, "bg-rose-400"],
                      ["Carbohydrates", state.plan.nutrition.carbs_g, "bg-amber-400"],
                      ["Fats", state.plan.nutrition.fats_g, "bg-lime-500"],
                      ["Fiber", state.plan.nutrition.fiber_g, "bg-emerald-600"],
                    ] as const
                  ).map(([label, grams, dot]) => (
                    <div key={label} className="flex items-center justify-between gap-1">
                      <dt className="flex items-center gap-[6px]">
                        <span aria-hidden="true" className={`size-[8px] rounded-full ${dot}`} />
                        {label}
                      </dt>
                      <dd>
                        <strong className="text-[14px] text-[#117d69]">{fmt(grams)}</strong> g
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>

            {/* Left / Right Balance */}
            <section className={`${cardClass} mt-[15px] p-[20px]`}>
              <h2 className="text-[10px] font-bold">Left / Right Balance</h2>
              {state.plan.exercises.detected_imbalances.length === 0 &&
              state.plan.exercises.unconfirmed_imbalance_pairs.length === 0 ? (
                <>
                  <p className="mt-[10px] inline-block rounded-[8px] bg-[#117d69]/20 px-[10px] py-[3px] text-[12px] font-bold text-[#0b5e4f]">
                    Your Muscles Are Well Balanced!
                  </p>
                  <p className="mt-[8px] text-[10px] leading-[1.5] text-black/75">
                    No significant muscle imbalances were found. Your left and right sides read
                    within 5% of each other, so no extra corrective exercises are needed right now.
                    Keep up your current routine.
                  </p>
                </>
              ) : (
                <>
                  {state.plan.exercises.detected_imbalances.length > 0 && (
                    <>
                      <p className="mt-[10px] inline-block rounded-[8px] bg-amber-200 px-[10px] py-[3px] text-[12px] font-bold text-amber-900">
                        Imbalance Detected
                      </p>
                      <ul className="mt-[8px] list-disc space-y-[2px] pl-4 text-[10px] text-black/75">
                        {state.plan.exercises.detected_imbalances.map((i) => (
                          <li key={i}>{i}</li>
                        ))}
                      </ul>
                      <p className="mt-[6px] text-[10px] text-black/60">
                        Your workout below includes single-side exercises to even this out.
                      </p>
                    </>
                  )}
                  {state.plan.exercises.unconfirmed_imbalance_pairs.length > 0 && (
                    <p className="mt-[8px] text-[10px] leading-[1.5] text-amber-800">
                      We didn&apos;t check balance for your{" "}
                      {state.plan.exercises.unconfirmed_imbalance_pairs.join(" and ")} because those
                      numbers weren&apos;t confirmed.{" "}
                      <Link className="font-bold underline" href="/preview">
                        Check them
                      </Link>{" "}
                      to get balance advice.
                    </p>
                  )}
                </>
              )}
            </section>

            {/* Recommended Workout */}
            <section className={`${cardClass} mt-[15px] p-[20px]`}>
              <h2 className="text-[10px] font-bold">Recommended Workout</h2>
              <ul className="mt-[16px] space-y-[8px]">
                {state.plan.exercises.exercises.map((ex) => (
                  <li
                    key={ex.name}
                    className="rounded-[8px] border border-[#d9d9d9] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] px-[15px] py-[9px] shadow-sm"
                  >
                    <p className="flex flex-wrap items-center gap-[8px] text-[12px] font-bold">
                      {ex.name}
                      <span className="rounded-[4px] bg-[#117d69]/20 px-[5px] py-[2px] text-[8px] font-bold text-[#0b5e4f]">
                        {MOVEMENT_TYPES[ex.movement_type]}
                      </span>
                    </p>
                    <p className="mt-[1px] text-[10px] text-black/70">
                      Target: {ex.target}
                      {ex.equipment ? ` (${ex.equipment})` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            </section>

            {/* Actions */}
            <div className="mt-[32px] space-y-[15px]">
              <button type="button" onClick={() => setDialog("summary")} className={btn.primary}>
                Simplify
              </button>
              <div className="flex gap-[15px]">
                <button type="button" onClick={() => setDialog("discard")} className={`${btn.light} text-[#117d69]`}>
                  <Icon name="trash" size={14} />
                  Discard
                </button>
                <button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={saveState === "saving"}
                  className={btn.primary}
                >
                  <Icon name={saveState === "saved" ? "check" : "save"} size={16} />
                  {saveState === "saving" ? "Saving…" : saveState === "saved" ? "Saved" : "Save"}
                </button>
              </div>
              {saveState === "error" && saveError && (
                <p role="alert" className="text-center text-[11px] text-rose-300">
                  {saveError}
                </p>
              )}
            </div>
          </>
        )}
      </div>

      {/* --- Popups ------------------------------------------------------------ */}

      {state.status === "ready" && profile && (
        <Modal open={dialog === "summary"} onClose={() => setDialog(null)} title="Summary" widthClass="max-w-[317px]">
          <div className="mt-[14px] text-[11px] leading-[1.5]">
            <p className="inline-block rounded-[6px] bg-[#117d69]/20 px-[8px] py-[2px] text-[12px] font-bold text-[#0b5e4f]">
              Daily Fitness and Nutrition Plan ({GOAL_LABELS[profile.fitness_goal]})
            </p>
            <h3 className="mt-[8px] font-bold">Nutritional Targets</h3>
            <ul className="text-black/80">
              <li>Daily Energy Target: {fmt(state.plan.nutrition.target_calories_kcal)} kcal</li>
              <li>
                BMR: {fmt(state.plan.nutrition.bmr_kcal)} kcal, TDEE: {fmt(state.plan.nutrition.tdee_kcal)} kcal
              </li>
              <li>Protein: {fmt(state.plan.nutrition.protein_g)} g</li>
              <li>Carbohydrates: {fmt(state.plan.nutrition.carbs_g)} g</li>
              <li>Fats: {fmt(state.plan.nutrition.fats_g)} g</li>
              <li>Fiber: {fmt(state.plan.nutrition.fiber_g)} g</li>
            </ul>

            <p className="mt-[12px] inline-block rounded-[6px] bg-[#117d69]/20 px-[8px] py-[2px] text-[12px] font-bold text-[#0b5e4f]">
              Recommended Workout Program
            </p>
            {state.plan.exercises.detected_imbalances.length > 0 && (
              <>
                <h3 className="mt-[8px] font-bold">Detected Imbalances and Focus Areas</h3>
                <ul className="text-black/80">
                  {state.plan.exercises.detected_imbalances.map((i) => (
                    <li key={i}>{i}</li>
                  ))}
                </ul>
              </>
            )}
            <h3 className="mt-[8px] font-bold">Exercise Routine</h3>
            <ul className="space-y-[4px] text-black/80">
              {state.plan.exercises.exercises.map((ex) => (
                <li key={ex.name}>
                  <span className="font-bold text-black">{ex.name}</span>{" "}
                  <span className="rounded-[4px] bg-[#117d69]/20 px-[4px] text-[8px] font-bold text-[#0b5e4f]">
                    {MOVEMENT_TYPES[ex.movement_type]}
                  </span>
                  <br />
                  Target: {ex.target}
                  {ex.equipment ? ` (${ex.equipment})` : ""}
                </li>
              ))}
            </ul>
            <p className="mt-[10px] text-[9px] text-black/50">
              General fitness information, not medical advice.
            </p>
          </div>
          <button type="button" onClick={handleCopy} className={`${btn.primary} mt-[18px]`}>
            <Icon name={copied ? "check" : "copy"} size={16} />
            {copied ? "Copied" : "Copy to clipboard"}
          </button>
          <button type="button" onClick={() => setDialog(null)} className={`${btn.secondary} mt-[8px]`}>
            <Icon name="close" size={14} />
            Close
          </button>
          <span className="sr-only" aria-live="polite">
            {copied ? "Summary copied to clipboard" : ""}
          </span>
        </Modal>
      )}

      <ConfirmDialog
        open={dialog === "discard"}
        title="Discard this report?"
        body={
          saveState === "saved"
            ? "The copy you saved stays on your dashboard. This only clears what's on screen."
            : "Are you sure you want to discard this InBody report? Your analysis results will be lost and cannot be recovered."
        }
        confirmLabel="Discard"
        confirmIcon="trash"
        onCancel={() => setDialog(null)}
        onConfirm={handleDiscard}
      />

      <Modal open={dialog === "saved"} onClose={() => setDialog(null)} title="Saved!">
        <p className="mt-3 text-center text-[12px] leading-relaxed text-black/70">
          Your scan and plan are saved to your account. You can see them, and how your numbers
          change over time, on your dashboard.
        </p>
        <Link href="/dashboard" className={`${btn.primary} mt-5`}>
          Go to Dashboard
        </Link>
        <button type="button" onClick={() => setDialog(null)} className={`${btn.secondary} mt-[8px]`}>
          Stay here
        </button>
      </Modal>

      <Modal open={dialog === "guestSave"} onClose={() => setDialog(null)} title="Save your scan">
        <p className="mt-3 text-center text-[12px] leading-relaxed text-black/70">
          Log in or create a free account to keep this scan and track your progress over time.
          Your results stay on screen while you do.
        </p>
        <Link href="/sign-up?redirect=/result%3Fsave%3D1" className={`${btn.primary} mt-5`}>
          Sign Up to Save
        </Link>
        <Link href="/sign-in?redirect=/result%3Fsave%3D1" className={`${btn.secondary} mt-[8px]`}>
          Log In
        </Link>
      </Modal>

      <Modal
        open={dialog === "duplicate" && duplicateScan !== null}
        onClose={() => setDialog(null)}
        title="Already saved"
        icon={<Icon name="alert" size={20} className="mt-[2px] text-amber-600" />}
      >
        <p className="mt-3 text-center text-[12px] leading-relaxed text-black/70">
          This scan matches one already in your history
          {duplicateScan?.created_at
            ? ` (saved ${new Date(duplicateScan.created_at).toLocaleDateString(undefined, {
                day: "numeric",
                month: "short",
                year: "numeric",
              })})`
            : ""}
          . View that one, or save this as a new entry?
        </p>
        {duplicateScan && (
          <Link href={`/history/${duplicateScan.id}`} className={`${btn.primary} mt-5`}>
            View saved scan
          </Link>
        )}
        <button
          type="button"
          onClick={() => void doSave()}
          disabled={saveState === "saving"}
          className={`${btn.secondary} mt-[8px]`}
        >
          {saveState === "saving" ? "Saving…" : "Save as new entry"}
        </button>
      </Modal>

      <Modal open={dialog === "sheet"} onClose={() => setDialog(null)} title="Your sheet" widthClass="max-w-[370px]">
        {sheetImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt="The InBody sheet these values were read from" src={sheetImage} className="mt-3 w-full rounded-[8px]" />
        )}
        <button type="button" onClick={() => setDialog(null)} className={`${btn.secondary} mt-4`}>
          Close
        </button>
      </Modal>
    </PhoneFrame>
  );
}

export default function Result() {
  return (
    <Suspense
      fallback={
        <PhoneFrame bg="bg-[#3e3e3e]">
          <div className="flex h-full items-center justify-center text-[14px] text-white">
            Loading results…
          </div>
        </PhoneFrame>
      }
    >
      <ResultContent />
    </Suspense>
  );
}
