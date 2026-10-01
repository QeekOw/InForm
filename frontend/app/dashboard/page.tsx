"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppHeader from "@/components/AppHeader";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import TrendChart, { type TrendPoint } from "@/components/TrendChart";
import { btn, cardClass } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { GOAL_LABELS } from "@/lib/profileOptions";
import { getCurrentScan, listScans, type CurrentPlanResponse, type ScanSummary } from "@/lib/scans";
import { ACTIVITY_LABELS, ageFromDob } from "@/lib/user";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; scans: ScanSummary[] };

// Fetched separately: a brand-new Account has no current plan (404) while
// still having a valid, empty scan list.
type CurrentPlanState =
  | { status: "loading" }
  | { status: "none" }
  | { status: "ready"; plan: CurrentPlanResponse };

/** Body composition only: the calorie target follows from the plan and goal,
 * it isn't a measurement of the person. */
const CHARTED_METRICS: {
  title: string;
  unit: string;
  decimals: number;
  value: (scan: ScanSummary) => number;
}[] = [
  { title: "Weight", unit: "kg", decimals: 1, value: (s) => s.weight_kg },
  { title: "Body Fat", unit: "%", decimals: 1, value: (s) => s.percent_body_fat },
  { title: "Skeletal Muscle Mass", unit: "kg", decimals: 1, value: (s) => s.skeletal_muscle_mass_kg },
  { title: "Lean Body Mass", unit: "kg", decimals: 1, value: (s) => s.lean_body_mass_kg },
];

function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export default function Dashboard() {
  const router = useRouter();
  const { account, loading: authLoading } = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });
  const [currentPlan, setCurrentPlan] = useState<CurrentPlanState>({ status: "loading" });

  useEffect(() => {
    if (authLoading) return;
    if (!account) {
      router.replace("/sign-in?redirect=/dashboard");
      return;
    }
    listScans()
      .then((scans) => setState({ status: "ready", scans }))
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? String(err.message) : "Couldn't load your scans.";
        setState({ status: "error", message });
      });
    getCurrentScan()
      .then((plan) => setCurrentPlan({ status: "ready", plan }))
      .catch(() => setCurrentPlan({ status: "none" }));
  }, [account, authLoading, router]);

  // `GET /scans` is newest-first; a chart reads left to right.
  const oldestFirst =
    state.status === "ready"
      ? [...state.scans].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      : [];

  const pointsFor = (value: (scan: ScanSummary) => number): TrendPoint[] =>
    oldestFirst.map((scan) => ({
      t: new Date(scan.created_at).getTime(),
      label: formatShortDate(scan.created_at),
      value: value(scan),
      corrected: scan.has_corrections,
    }));

  const age = account?.date_of_birth ? ageFromDob(account.date_of_birth) : null;
  const displayName = account?.name || account?.email.split("@")[0] || "";
  const scanCount = state.status === "ready" ? state.scans.length : null;
  const anyCorrected = oldestFirst.some((scan) => scan.has_corrections);

  const stats: { label: string; value: string }[] = [
    { label: "Age", value: age !== null ? String(age) : "—" },
    {
      label: "Biological Sex",
      value: account?.default_biological_sex === "female" ? "Female" : account?.default_biological_sex === "male" ? "Male" : "—",
    },
    {
      label: "Activity",
      value:
        account?.default_activity_multiplier != null
          ? ACTIVITY_LABELS[account.default_activity_multiplier] ?? `${account.default_activity_multiplier}x`
          : "—",
    },
    { label: "Goal", value: account?.default_fitness_goal ? GOAL_LABELS[account.default_fitness_goal] : "—" },
  ];

  return (
    <PhoneFrame bg="bg-[#3e3e3e]" scrollable>
      <AppHeader />

      <div className="px-[30px] pb-[24px] text-[#fcfcfc]">
        <h1 className="mt-[31px] flex flex-wrap items-baseline gap-x-[14px]">
          <span className="text-[40px] font-bold leading-none tracking-[0.02em]">Hello!</span>
          <span className="truncate text-[25px] font-medium">{displayName}</span>
        </h1>

        <section className={`${cardClass} mt-[16px] p-[20px]`} aria-label="Your profile">
          <dl className="grid grid-cols-2 gap-x-[20px] gap-y-[16px]">
            {stats.map((s) => (
              <div key={s.label}>
                <dt className="text-[10px] text-black/70">{s.label}</dt>
                <dd className="mt-[5px] text-[14px] font-bold">{s.value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-[6px] flex items-baseline justify-end gap-[6px] text-[8px] text-black/70">
            Total Scan <span className="text-[14px] font-bold text-[#117d69]">{scanCount ?? "…"}</span>
          </p>
          <Link href="/upload" className={`${btn.primary} mt-[8px]`}>
            <Icon name="fileAdd" size={16} />
            New Scan
          </Link>
        </section>

        {(authLoading || state.status === "loading") && (
          <p role="status" className="mt-[32px] text-center text-[12px] text-white/60">
            Loading your scans…
          </p>
        )}

        {state.status === "error" && (
          <div role="alert" className={`${cardClass} mt-[32px] p-[18px] text-center text-[12px]`}>
            <p className="font-bold text-rose-700">Couldn&apos;t load your scans</p>
            <p className="mt-1 text-black/70">{state.message}</p>
          </div>
        )}

        {state.status === "ready" && state.scans.length === 0 && (
          <div className={`${cardClass} mt-[32px] p-[24px] text-center`}>
            <p className="text-[14px] font-bold">No scans yet</p>
            <p className="mt-2 text-[12px] leading-relaxed text-black/70">
              Save your first scan and this becomes a record of how your body composition moves
              over time.
            </p>
          </div>
        )}

        {state.status === "ready" && state.scans.length > 0 && (
          <>
            {/* A calm note, never a reason to hide or recompute the plan. */}
            {currentPlan.status === "ready" && currentPlan.plan.is_stale && (
              <p className="mt-[20px] rounded-[8px] bg-amber-400/15 p-[12px] text-[11px] leading-relaxed text-amber-100">
                Your latest plan is {currentPlan.plan.age_days} days old. It&apos;s still an accurate
                record of you then, but a new scan will bring it up to date.
              </p>
            )}

            <h2 className="mt-[32px] text-[12px] font-bold">
              {state.scans.length === 1 ? "Where you are now" : "How you’ve moved"}
            </h2>
            {state.scans.length === 1 && (
              <p className="mt-1 text-[10px] text-white/60">
                One scan is a starting point, not a trend. Scan again to see movement.
              </p>
            )}
            <div className="mt-[13px] space-y-[15px]">
              {CHARTED_METRICS.map((m) => (
                <TrendChart key={m.title} title={m.title} unit={m.unit} decimals={m.decimals} points={pointsFor(m.value)} />
              ))}
            </div>
            {anyCorrected && (
              <p className="mt-3 text-[10px] leading-relaxed text-white/60">
                Scans marked <span className="font-bold text-sky-300">Edited</span> include a value
                you typed in from your sheet.
              </p>
            )}
            <Link href="/history" className="mt-[20px] block text-center text-[12px] font-bold text-[#7ee0cf] underline">
              See every scan
            </Link>
          </>
        )}

        <p className="mt-[44px] text-center text-[10px] text-[#fcfcfc]/60">
          © 2026 InForm. For educational purposes only.
        </p>
      </div>
    </PhoneFrame>
  );
}
