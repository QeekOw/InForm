"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import { loadJSON, saveJSON } from "@/lib/session";
import {
  DEFAULT_READING,
  SESSION_KEYS,
  type InBodyReading,
  type SampleExtraction,
} from "@/lib/inbody";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";
const imgEdit = "/icons/preview/edit-icon.svg";

function Row({
  label,
  value,
  unit,
  isFlagged = false,
}: {
  label: string;
  value: string | number;
  unit: string;
  isFlagged?: boolean;
}) {
  return (
    <div
      className={`flex items-baseline justify-between py-1 text-[12px] ${
        isFlagged ? "bg-amber-50 -mx-2 px-2 rounded border border-amber-200" : ""
      }`}
    >
      <span className="flex items-center gap-1.5">
        <span>{label}</span>
        {isFlagged && (
          <span className="rounded bg-amber-200 px-1 py-0.2 text-[8px] font-bold text-amber-800">
            Flagged Check
          </span>
        )}
      </span>
      <span className="font-bold">
        {value} <span className="text-[8px] font-medium">{unit}</span>
      </span>
    </div>
  );
}

export default function Preview() {
  const router = useRouter();
  const [reading, setReading] = useState<InBodyReading | null>(null);
  const [extraction, setExtraction] = useState<SampleExtraction | null>(null);
  const [sampleId, setSampleId] = useState<string | null>(null);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR
    // eslint-disable-next-line react-hooks/set-state-in-effect
    const loadedExtraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    const loadedSampleId = loadJSON<string>(SESSION_KEYS.sampleId);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    const storedReading = loadJSON<InBodyReading>(SESSION_KEYS.reading);

    setExtraction(loadedExtraction);
    setSampleId(loadedSampleId);

    if (loadedExtraction?.status === "refused") {
      setReading(null);
    } else if (storedReading) {
      setReading(storedReading);
    } else {
      setReading(DEFAULT_READING);
    }
  }, []);

  const handleConfirm = () => {
    if (reading) {
      saveJSON(SESSION_KEYS.reading, reading);
      router.push("/result");
    }
  };

  const isRefused = extraction?.status === "refused";
  const flaggedFields = new Set(extraction?.flagged ?? []);
  const seg = reading?.segmental_lean;

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="max-h-screen overflow-y-auto pb-10">
        <div className="flex items-center gap-3 px-[30px] pt-[62px]">
          <Link
            href="/upload"
            className="flex size-8 items-center justify-center rounded-full bg-white shadow-md"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="Back" className="size-[18px]" src={imgBack} />
          </Link>
          <h1 className="text-[24px] font-bold text-[#fcfcfc]">Preview</h1>
        </div>

        {/* Report Photo Preview */}
        <div className="relative mx-[30px] mt-[25px] h-[201px] overflow-hidden rounded-[15px] bg-[#1f1f1f]">
          {sampleId ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt="Sample report"
              className="size-full object-cover opacity-90"
              src={`${API_URL}/samples/${sampleId}/image`}
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
          ) : (
            <p className="absolute inset-0 flex items-center justify-center text-[12px] text-white/40">
              Your report photo
            </p>
          )}

          <Link
            href="/upload"
            className="absolute right-4 top-4 flex h-8 items-center gap-[10px] rounded-lg bg-[#117d69] px-[10px] text-[12px] font-bold text-white shadow"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-[14px]" src={imgCamera} />
            Change Sheet
          </Link>
        </div>

        {/* Refused State View */}
        {isRefused ? (
          <div className="mx-[30px] mt-[18px] rounded-[15px] border-2 border-rose-500/50 bg-white p-[25px] text-black">
            <div className="flex items-center gap-2">
              <span className="rounded bg-rose-600 px-2 py-0.5 text-[10px] font-bold text-white uppercase">
                Model Refusal
              </span>
              <h2 className="text-[14px] font-bold text-rose-900">Sheet Declined (Fail-Closed)</h2>
            </div>
            <p className="mt-3 text-[12px] leading-relaxed text-zinc-700">
              {extraction?.message ??
                "This document was rejected because required fields could not be read with certainty."}
            </p>
            <div className="mt-4 rounded-lg bg-zinc-100 p-3 text-[11px] text-zinc-600">
              <p className="font-bold text-zinc-800">Why did this happen?</p>
              <p className="mt-1">
                InForm strictly fails closed on non-InBody documents and obscured fields to prevent fabricating clinical metrics (ADR-0008).
              </p>
            </div>
            <Link
              href="/upload"
              className="mt-5 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white"
            >
              ← Choose another sample sheet
            </Link>
          </div>
        ) : reading && seg ? (
          /* Normal / Flagged Extraction View */
          <div className="mx-[30px] mt-[18px] rounded-[15px] bg-white p-[25px] text-black">
            {flaggedFields.size > 0 && (
              <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-2.5 text-[11px] text-amber-900">
                <span className="font-bold">Notice:</span> One or more values triggered physiological cross-checks. You can review and edit them below before confirming.
              </div>
            )}

            <h2 className="text-[14px] font-bold">Body Composition</h2>
            <div className="mt-3">
              <Row
                label="Weight"
                value={reading.weight_kg}
                unit="kg"
                isFlagged={flaggedFields.has("weight_kg")}
              />
              <Row
                label="Lean Body Mass"
                value={reading.lean_body_mass_kg}
                unit="kg"
                isFlagged={flaggedFields.has("lean_body_mass_kg")}
              />
              <Row
                label="Percent Body Fat"
                value={reading.percent_body_fat}
                unit="%"
                isFlagged={flaggedFields.has("percent_body_fat")}
              />
              <Row
                label="Skeletal Muscle Mass"
                value={reading.skeletal_muscle_mass_kg}
                unit="kg"
                isFlagged={flaggedFields.has("skeletal_muscle_mass_kg")}
              />
              <Row
                label="Visceral Fat Level"
                value={`Level ${reading.visceral_fat_level}`}
                unit=""
              />
            </div>

            <div className="my-4 h-px bg-black/10" />

            <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
            <div className="mt-3 grid grid-cols-2 gap-x-6">
              <div>
                <Row
                  label="Left Arm"
                  value={seg.left_arm_kg}
                  unit="kg"
                  isFlagged={flaggedFields.has("segmental_lean.left_arm_kg")}
                />
                <Row
                  label="Right Arm"
                  value={seg.right_arm_kg}
                  unit="kg"
                  isFlagged={flaggedFields.has("segmental_lean.right_arm_kg")}
                />
                <Row
                  label="Trunk"
                  value={seg.trunk_kg}
                  unit="kg"
                  isFlagged={flaggedFields.has("segmental_lean.trunk_kg")}
                />
              </div>
              <div>
                <Row
                  label="Left Leg"
                  value={seg.left_leg_kg}
                  unit="kg"
                  isFlagged={flaggedFields.has("segmental_lean.left_leg_kg")}
                />
                <Row
                  label="Right Leg"
                  value={seg.right_leg_kg}
                  unit="kg"
                  isFlagged={flaggedFields.has("segmental_lean.right_leg_kg")}
                />
              </div>
            </div>

            <div className="my-4 h-px bg-black/10" />

            <Row
              label="Basal Metabolic Rate"
              value={reading.basal_metabolic_rate_kcal}
              unit="kcal"
              isFlagged={flaggedFields.has("basal_metabolic_rate_kcal")}
            />

            <Link
              href="/preview/edit"
              className="mt-6 flex h-[40px] w-full items-center justify-center gap-[10px] rounded-lg border-[1.5px] border-[#117d69] text-[14px] font-bold text-[#117d69]"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img alt="" className="size-3" src={imgEdit} />
              Edit
            </Link>
            <button
              type="button"
              onClick={handleConfirm}
              className="mt-2 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white shadow-sm"
            >
              Confirm
            </button>
          </div>
        ) : (
          <div className="mx-[30px] mt-[18px] rounded-[15px] bg-white p-[25px] text-center text-zinc-600">
            <p className="text-[13px]">No InBody reading data available.</p>
            <Link
              href="/upload"
              className="mt-3 inline-block text-[12px] font-bold text-[#117d69]"
            >
              ← Return to Upload
            </Link>
          </div>
        )}
      </div>
    </PhoneFrame>
  );
}
