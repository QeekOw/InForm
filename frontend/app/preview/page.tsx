"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { API_URL } from "@/lib/config";
import { confirmReading } from "@/lib/flow";
import {
  BMR_FIELD,
  BODY_COMPOSITION_FIELDS,
  DEFAULT_READING,
  SEGMENTAL_LEAN_COLUMNS,
  type InBodyPayload,
  type SampleExtraction,
} from "@/lib/inbody";
import { loadJSON, SESSION_KEYS } from "@/lib/session";

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
  value: string | number | null;
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
        {value ?? "—"}{" "}
        {value != null && unit && <span className="text-[8px] font-medium">{unit}</span>}
      </span>
    </div>
  );
}

export default function Preview() {
  const router = useRouter();
  const [reading, setReading] = useState<InBodyPayload | null>(null);
  const [extraction, setExtraction] = useState<SampleExtraction | null>(null);
  const [sampleId, setSampleId] = useState<string | null>(null);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    const loadedExtraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);
    const loadedSampleId = loadJSON<string>(SESSION_KEYS.sampleId);
    const storedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExtraction(loadedExtraction);
    setSampleId(loadedSampleId);

    if (loadedExtraction?.status === "refused") {
      setReading(null);
    } else {
      setReading(storedReading ?? DEFAULT_READING);
    }
  }, []);

  const handleConfirm = () => {
    if (reading) router.push(confirmReading(reading));
  };

  const isRefused = extraction?.status === "refused";
  const flaggedFields = new Set(extraction?.flagged ?? []);
  const isDemoReading =
    !sampleId && reading !== null && JSON.stringify(reading) === JSON.stringify(DEFAULT_READING);

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
            <ReportPhoto />
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
        ) : reading && reading.segmental_lean ? (
          /* Normal / Flagged Extraction View */
          <>
            {isDemoReading && (
              <div className="mx-[30px] mt-3 flex items-center justify-between rounded-lg bg-white/10 px-3 py-1.5 text-[11px] text-white/90">
                <span className="font-medium">Demo baseline values</span>
                <span className="text-[10px] text-white/60">Pending OCR extraction · edit below</span>
              </div>
            )}

            <div
              className={`mx-[30px] rounded-[15px] bg-white p-[25px] text-black ${
                isDemoReading ? "mt-[14px]" : "mt-[18px]"
              }`}
            >
              {flaggedFields.size > 0 && (
                <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-2.5 text-[11px] text-amber-900">
                  <span className="font-bold">Notice:</span> One or more values triggered physiological cross-checks. You can review and edit them below before confirming.
                </div>
              )}

              <h2 className="text-[14px] font-bold">Body Composition</h2>
              <div className="mt-3">
                {BODY_COMPOSITION_FIELDS.map((field) => {
                  const value = reading[field.key];
                  return (
                    <Row
                      key={field.key}
                      label={field.label}
                      value={value != null && field.formatValue ? field.formatValue(value) : value}
                      unit={field.unit}
                      isFlagged={flaggedFields.has(field.key)}
                    />
                  );
                })}
              </div>

              <div className="my-4 h-px bg-black/10" />

              <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
              <div className="mt-3 grid grid-cols-2 gap-x-6">
                {SEGMENTAL_LEAN_COLUMNS.map((column) => (
                  <div key={column[0].key}>
                    {column.map((field) => (
                      <Row
                        key={field.key}
                        label={field.label}
                        value={reading.segmental_lean[field.key]}
                        unit={field.unit}
                        isFlagged={flaggedFields.has(`segmental_lean.${field.key}`)}
                      />
                    ))}
                  </div>
                ))}
              </div>

              <div className="my-4 h-px bg-black/10" />

              <Row
                label={BMR_FIELD.label}
                value={reading[BMR_FIELD.key]}
                unit={BMR_FIELD.unit}
                isFlagged={flaggedFields.has(BMR_FIELD.key)}
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
          </>
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
