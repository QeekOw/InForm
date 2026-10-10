"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import PhoneFrame from "@/components/PhoneFrame";
import { EditedMarker } from "@/components/FieldStatus";
import { btn, cardClass } from "@/components/ui";
import { useAuth } from "@/lib/AuthProvider";
import { ApiError } from "@/lib/api";
import { listScans, type ScanSummary } from "@/lib/scans";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; scans: ScanSummary[] };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });
}

export default function History() {
  const router = useRouter();
  const { account, loading: authLoading } = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    if (authLoading) return;
    if (!account) {
      router.replace("/sign-in?redirect=/history");
      return;
    }
    listScans()
      .then((scans) => setState({ status: "ready", scans }))
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? String(err.message) : "Couldn't load your history.";
        setState({ status: "error", message });
      });
  }, [account, authLoading, router]);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <header className="flex h-[120px] items-start justify-between bg-gradient-to-b from-black/60 to-transparent px-[30px] pt-[48px]">
        <BackButton href="/dashboard" label="Back to dashboard" />
        <h1 className="text-[24px] font-bold tracking-[0.02em] text-[#fcfcfc]">History</h1>
      </header>

      <div className="px-[30px] pb-[40px] pt-[30px]">
        {(authLoading || state.status === "loading") && (
          <p role="status" className="text-center text-[12px] text-white/60">
            Loading your history…
          </p>
        )}

        {state.status === "error" && (
          <div role="alert" className={`${cardClass} p-[18px] text-center text-[12px]`}>
            <p className="font-bold text-rose-700">Couldn&apos;t load your history</p>
            <p className="mt-1 text-black/70">{state.message}</p>
          </div>
        )}

        {state.status === "ready" && state.scans.length === 0 && (
          <div className={`${cardClass} p-[24px] text-center`}>
            <p className="text-[14px] font-bold">No scans yet</p>
            <p className="mt-2 text-[12px] text-black/70">
              Take your first scan to start tracking your body composition over time.
            </p>
            <Link href="/upload" className={`${btn.primary} mt-4`}>
              Take your first scan
            </Link>
          </div>
        )}

        {state.status === "ready" && state.scans.length > 0 && (
          <ul className="space-y-[15px]">
            {state.scans.map((scan) => (
              <li key={scan.id}>
                <Link
                  href={`/history/${scan.id}`}
                  className={`${cardClass} block px-[20px] py-[15px] transition-shadow hover:ring-2 hover:ring-white/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf]`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[12px] font-bold">{formatDate(scan.created_at)}</p>
                    {scan.has_corrections && (
                      <span className="flex items-center gap-[5px] text-[9px] text-black/60">
                        <EditedMarker /> Includes edited values
                      </span>
                    )}
                  </div>
                  <div className="my-[10px] h-px bg-black/15" />
                  <dl className="grid grid-cols-4 gap-1 text-center">
                    {(
                      [
                        [Math.round(scan.target_calories_kcal), "kcal target"],
                        [scan.weight_kg.toFixed(1), "weight (kg)"],
                        [scan.percent_body_fat.toFixed(1), "body fat (%)"],
                        [scan.skeletal_muscle_mass_kg.toFixed(1), "muscle (kg)"],
                      ] as const
                    ).map(([value, label]) => (
                      <div key={label} className="flex flex-col-reverse">
                        <dt className="text-[8px] text-black/60">{label}</dt>
                        <dd className="text-[16px] font-bold text-[#117d69]">{value}</dd>
                      </div>
                    ))}
                  </dl>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </PhoneFrame>
  );
}
