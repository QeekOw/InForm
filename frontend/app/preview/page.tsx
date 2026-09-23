"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { API_URL } from "@/lib/config";
import { getFieldLabel, getUnresolvedFlagged, normalizeFieldKey } from "@/lib/corrections";
import { confirmReading } from "@/lib/flow";
import {
  BMR_FIELD,
  BODY_COMPOSITION_FIELDS,
  DEFAULT_READING,
  SEGMENTAL_LEAN_COLUMNS,
  type InBodyPayload,
  type SampleExtraction,
} from "@/lib/inbody";
import {
  refusedSheetCopy,
  sheetSwapAction,
  unrecognizedSheetCopy,
  type SheetSource,
  type SheetVariant,
} from "@/lib/photo";
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";
const imgEdit = "/icons/preview/edit-icon.svg";

function Row({
  label,
  value,
  unit,
  isFlagged = false,
  isUnread = false,
  isCorrected = false,
  isConfirmed = false,
  requiresConfirmation = false,
  onConfirm,
}: {
  label: string;
  value: string | number | null;
  unit: string;
  isFlagged?: boolean;
  isUnread?: boolean;
  isCorrected?: boolean;
  isConfirmed?: boolean;
  requiresConfirmation?: boolean;
  onConfirm?: () => void;
}) {
  let containerBg = "";
  if (isUnread) containerBg = "bg-rose-50 -mx-2 px-2 rounded border border-rose-200";
  else if (isFlagged && !isCorrected && !isConfirmed) containerBg = "bg-amber-50 -mx-2 px-2 rounded border border-amber-200";
  else if (isConfirmed && !isCorrected) containerBg = "bg-emerald-50 -mx-2 px-2 rounded border border-emerald-200";
  else if (isCorrected) containerBg = "bg-sky-50 -mx-2 px-2 rounded border border-sky-200";

  return (
    <div className={`flex items-baseline justify-between py-1 text-[12px] ${containerBg}`}>
      <span className="flex items-center gap-1.5">
        <span>{label}</span>
        {isUnread && (
          <span className="rounded bg-rose-200 px-1 py-0.5 text-[8px] font-bold text-rose-800">
            Unread
          </span>
        )}
        {(isFlagged || requiresConfirmation) && !isCorrected && !isConfirmed && (
          <span className="inline-flex items-center gap-1">
            <span className="rounded bg-amber-200 px-1 py-0.5 text-[8px] font-bold text-amber-800">
              {isFlagged ? "Flagged Check" : "Check sheet"}
            </span>
            {onConfirm && (
              <button
                type="button"
                onClick={onConfirm}
                aria-label={`Confirm ${label} matches your InBody sheet`}
                className="min-h-6 min-w-6 rounded bg-[#117d69] px-1.5 py-0.5 text-[8px] font-bold text-white shadow-xs hover:bg-[#0e6353]"
              >
                Confirm
              </button>
            )}
          </span>
        )}
        {isConfirmed && !isCorrected && (
          <span className="inline-flex items-center gap-1">
            <span className="rounded bg-emerald-200 px-1 py-0.5 text-[8px] font-bold text-emerald-800">
              ✓ Confirmed
            </span>
            {onConfirm && (
              <button
                type="button"
                onClick={onConfirm}
                className="min-h-6 min-w-6 text-[8px] font-medium text-zinc-500 hover:text-zinc-700 underline"
                title="Undo confirmation"
              >
                Undo
              </button>
            )}
          </span>
        )}
        {isCorrected && (
          <span className="rounded bg-sky-200 px-1 py-0.5 text-[8px] font-bold text-sky-800">
            Corrected
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
  const [sheetSource, setSheetSource] = useState<SheetSource>("photo");
  const [corrections, setCorrections] = useState<Record<string, unknown>>({});
  const [confirmedFields, setConfirmedFields] = useState<Set<string>>(new Set());

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    const loadedExtraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);
    const loadedSampleId = loadJSON<string>(SESSION_KEYS.sampleId);
    const storedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);
    const storedCorrections = loadJSON<Record<string, unknown>>(SESSION_KEYS.corrections) ?? {};
    const storedConfirmations = loadJSON<string[]>(SESSION_KEYS.confirmations) ?? [];

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExtraction(loadedExtraction);
    setSampleId(loadedSampleId);
    setSheetSource(loadJSON<SheetSource>(SESSION_KEYS.sheetSource) ?? "photo");
    setCorrections(storedCorrections);
    setConfirmedFields(new Set(storedConfirmations.map(normalizeFieldKey)));

    // Hard refuse on non-InBody documents or zero-read floor cases (ADR-0008 Amendment §3)
    const isHardRefusalCase =
      loadedExtraction?.error === "not_an_inbody_sheet" ||
      (loadedExtraction?.status === "refused" && loadedExtraction?.data == null);

    if (isHardRefusalCase) {
      setReading(null);
    } else if (storedReading) {
      setReading(storedReading);
    } else if (loadedExtraction?.data) {
      setReading(loadedExtraction.data);
    } else {
      setReading(DEFAULT_READING);
    }
  }, []);

  const isNotAnInBodySheet =
    extraction?.error === "not_an_inbody_sheet" ||
    (extraction?.message?.toLowerCase().includes("not appear to be an inbody") ?? false);

  // A sample sheet is talked about as a sample; otherwise the person's own
  // upload is named for what they actually picked (issue #83).
  const sheetVariant: SheetVariant = sampleId ? "sample" : sheetSource;
  const refusalCopy = refusedSheetCopy(sheetVariant);
  const unrecognizedCopy = unrecognizedSheetCopy(sheetVariant);
  const swapAction = sheetSwapAction(sheetVariant);

  const isRefusedSheet =
    !isNotAnInBodySheet &&
    (extraction?.status === "refused" ||
      (reading === null && extraction !== null && extraction?.data == null));

  const nonSheetMessage =
    extraction?.message ??
    "This image does not appear to be an InBody result sheet. Please upload a clear photo of your InBody 270 sheet.";
  const flaggedFields = new Set((extraction?.flagged ?? []).map(normalizeFieldKey));
  const unreadFromExtraction = new Set((extraction?.unread ?? []).map(normalizeFieldKey));
  const correctedFields = new Set(Object.keys(corrections).map(normalizeFieldKey));

  // Determine which flagged fields remain unconfirmed and uncorrected
  const unresolvedFlagged = getUnresolvedFlagged(
    extraction?.flagged,
    corrections,
    confirmedFields,
  );

  const handleToggleConfirm = (fieldKey: string) => {
    const norm = normalizeFieldKey(fieldKey);
    setConfirmedFields((prev) => {
      const next = new Set(prev);
      if (next.has(norm)) {
        next.delete(norm);
      } else {
        next.add(norm);
      }
      saveJSON(SESSION_KEYS.confirmations, Array.from(next));
      return next;
    });
  };

  const handleConfirm = () => {
    if (reading && remainingUnread.length === 0 && unresolvedFlagged.length === 0) {
      router.push(
        confirmReading(
          reading,
          corrections as Record<string, number>,
          extraction?.data,
          Array.from(confirmedFields),
        ),
      );
    }
  };

  // Determine which required fields are still missing / unread
  const remainingUnread: string[] = [];
  if (reading) {
    if (reading.weight_kg == null) remainingUnread.push("weight_kg");
    if (reading.lean_body_mass_kg == null) remainingUnread.push("lean_body_mass_kg");
    if (reading.percent_body_fat == null) remainingUnread.push("percent_body_fat");
    if (reading.skeletal_muscle_mass_kg == null) remainingUnread.push("skeletal_muscle_mass_kg");
    if (reading.basal_metabolic_rate_kcal == null) remainingUnread.push("basal_metabolic_rate_kcal");
    if (reading.segmental_lean) {
      if (reading.segmental_lean.left_arm_kg == null) remainingUnread.push("segmental_lean.left_arm_kg");
      if (reading.segmental_lean.right_arm_kg == null) remainingUnread.push("segmental_lean.right_arm_kg");
      if (reading.segmental_lean.left_leg_kg == null) remainingUnread.push("segmental_lean.left_leg_kg");
      if (reading.segmental_lean.right_leg_kg == null) remainingUnread.push("segmental_lean.right_leg_kg");
      if (reading.segmental_lean.trunk_kg == null) remainingUnread.push("segmental_lean.trunk_kg");
    }
  }

  const isDemoReading =
    !sampleId && reading !== null && JSON.stringify(reading) === JSON.stringify(DEFAULT_READING);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="pb-10">
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

          {/* A picked Sample sheet is swapped from the gallery, your own photo
              is retaken, and a PDF is replaced with another file. */}
          <Link
            href={swapAction.href}
            className="absolute right-4 top-4 flex h-8 items-center gap-[10px] rounded-lg bg-[#117d69] px-[10px] text-[12px] font-bold text-white shadow"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-[14px]" src={imgCamera} />
            {swapAction.label}
          </Link>
        </div>

        {/* State 1: Not an InBody Sheet State. Where a PDF whose page 1 is a
            cover sheet lands, so the way out is worded for what was uploaded
            (issue #83). */}
        {isNotAnInBodySheet ? (
          <div className="mx-[30px] mt-[18px] rounded-[15px] bg-white p-[25px] text-black shadow-sm border border-black/5">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-[10px] font-semibold text-zinc-600">
                {unrecognizedCopy.badge}
              </span>
            </div>
            <h2 className="mt-2 text-[16px] font-bold text-zinc-900">
              {unrecognizedCopy.heading}
            </h2>
            <p className="mt-2 text-[12px] leading-relaxed text-zinc-700">
              {nonSheetMessage}
            </p>
            <div className="mt-4 rounded-xl bg-zinc-50 border border-zinc-100 p-3 text-[11px] leading-relaxed text-zinc-600">
              <p className="font-bold text-zinc-800">{unrecognizedCopy.asideHeading}</p>
              <p className="mt-1">{unrecognizedCopy.aside}</p>
            </div>
            <Link
              href={unrecognizedCopy.primary.href}
              className="mt-5 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white shadow-sm hover:bg-[#0e6857] transition-colors"
            >
              {unrecognizedCopy.primary.label}
            </Link>
            <Link
              href={unrecognizedCopy.secondary.href}
              className="mt-2 flex h-[38px] w-full items-center justify-center rounded-lg border border-zinc-200 bg-white text-[12px] font-semibold text-zinc-700 hover:bg-zinc-50 transition-colors"
            >
              {unrecognizedCopy.secondary.label}
            </Link>
          </div>
        ) : isRefusedSheet ? (
          /* State 2: Whole-sheet refusal / engine refuses entirely. The wording
             follows what the person gave us — a sample, a photo, or a PDF page
             (issue #83) — while the refusal itself is the same either way. */
          <div className="mx-[30px] mt-[18px] rounded-[15px] bg-white p-[25px] text-black shadow-sm border border-black/5">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-[10px] font-semibold text-zinc-600">
                {refusalCopy.badge}
              </span>
            </div>
            <h2 className="mt-2 text-[16px] font-bold text-zinc-900">{refusalCopy.heading}</h2>
            <p className="mt-2 text-[12px] leading-relaxed text-zinc-700">{refusalCopy.body}</p>
            <div className="mt-4 rounded-xl bg-zinc-50 border border-zinc-100 p-3 text-[11px] leading-relaxed text-zinc-600">
              <p className="font-bold text-zinc-800">{refusalCopy.asideHeading}</p>
              <p className="mt-1">{refusalCopy.aside}</p>
            </div>
            <Link
              href={refusalCopy.primary.href}
              className="mt-5 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white shadow-sm hover:bg-[#0e6857] transition-colors"
            >
              {refusalCopy.primary.label}
            </Link>
            <Link
              href={refusalCopy.secondary.href}
              className="mt-2 flex h-[38px] w-full items-center justify-center rounded-lg border border-zinc-200 bg-white text-[12px] font-semibold text-zinc-700 hover:bg-zinc-50 transition-colors"
            >
              {refusalCopy.secondary.label}
            </Link>
          </div>
        ) : reading && reading.segmental_lean ? (
          /* Normal / Partial / Flagged Extraction View */
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
              {/* Unread Fields Notice (AC: Unread fields are named individually, not reported as a whole-sheet failure) */}
              {remainingUnread.length > 0 && (
                <div className="mb-4 rounded-lg border border-rose-300 bg-rose-50 p-2.5 text-[11px] text-rose-900">
                  <span className="font-bold">Unread fields:</span> The model could not read{" "}
                  <span className="font-semibold">
                    {remainingUnread.map(getFieldLabel).join(", ")}
                  </span>
                  . Type the values off your sheet below before building your plan.
                </div>
              )}

              {/* Flagged Fields Notice */}
              {unresolvedFlagged.length > 0 ? (
                <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-2.5 text-[11px] text-amber-900">
                  <span className="font-bold">Flagged fields:</span> The model read values that triggered physiological cross-checks for{" "}
                  <span className="font-semibold">
                    {unresolvedFlagged.map(getFieldLabel).join(", ")}
                  </span>
                  . Compare with your sheet and tap <strong>Confirm</strong> if correct, or <strong>Edit</strong> to correct.
                </div>
              ) : flaggedFields.size > 0 ? (
                <div className="mb-4 rounded-lg border border-emerald-300 bg-emerald-50 p-2.5 text-[11px] text-emerald-900">
                  <span className="font-bold">All flagged fields verified:</span> You have confirmed or corrected all flagged values.
                </div>
              ) : null}

              <h2 className="text-[14px] font-bold">Body Composition</h2>
              <div className="mt-3">
                {BODY_COMPOSITION_FIELDS.map((field) => {
                  const value = reading[field.key];
                  const isUnread = value == null || unreadFromExtraction.has(field.key);
                  const isCorrected = correctedFields.has(field.key);
                  const isConfirmed = confirmedFields.has(field.key);
                  const unit = field.key === "visceral_fat_level" ? "level" : field.unit;

                  return (
                    <Row
                      key={field.key}
                      label={field.label}
                      value={value != null && field.formatValue ? field.formatValue(value) : value}
                      unit={unit}
                      isUnread={isUnread && !isCorrected}
                      isFlagged={flaggedFields.has(field.key)}
                      isCorrected={isCorrected}
                      isConfirmed={isConfirmed}
                      onConfirm={() => handleToggleConfirm(field.key)}
                    />
                  );
                })}
              </div>

              <div className="my-4 h-px bg-black/10" />

              <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
              <p className="mt-1 text-[10px] text-zinc-600">
                Check both arm and leg readings against your sheet. Unconfirmed pairs won’t be assessed for imbalance.
              </p>
              <div className="mt-3 grid grid-cols-2 gap-x-6">
                {SEGMENTAL_LEAN_COLUMNS.map((column) => (
                  <div key={column[0].key}>
                    {column.map((field) => {
                      const dottedKey = `segmental_lean.${field.key}`;
                      const value = reading.segmental_lean[field.key];
                      const isUnread = value == null || unreadFromExtraction.has(dottedKey);
                      const isCorrected = correctedFields.has(dottedKey);
                      const isConfirmed = confirmedFields.has(dottedKey);

                      return (
                        <Row
                          key={field.key}
                          label={field.label}
                          value={value}
                          unit={field.unit}
                          isUnread={isUnread && !isCorrected}
                          isFlagged={flaggedFields.has(dottedKey)}
                          isCorrected={isCorrected}
                          isConfirmed={isConfirmed}
                          requiresConfirmation={field.key !== "trunk_kg"}
                          onConfirm={() => handleToggleConfirm(dottedKey)}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>

              <div className="my-4 h-px bg-black/10" />

              {(() => {
                const isUnread = reading[BMR_FIELD.key] == null || unreadFromExtraction.has(BMR_FIELD.key);
                const isCorrected = correctedFields.has(BMR_FIELD.key);
                const isConfirmed = confirmedFields.has(BMR_FIELD.key);
                return (
                  <Row
                    label={BMR_FIELD.label}
                    value={reading[BMR_FIELD.key]}
                    unit={BMR_FIELD.unit}
                    isUnread={isUnread && !isCorrected}
                    isFlagged={flaggedFields.has(BMR_FIELD.key)}
                    isCorrected={isCorrected}
                    isConfirmed={isConfirmed}
                    onConfirm={() => handleToggleConfirm(BMR_FIELD.key)}
                  />
                );
              })()}

              <Link
                href="/preview/edit"
                className={`mt-6 flex h-[40px] w-full items-center justify-center gap-[10px] rounded-lg text-[14px] font-bold ${
                  remainingUnread.length > 0
                    ? "bg-[#117d69] text-white shadow-sm"
                    : "border-[1.5px] border-[#117d69] text-[#117d69]"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt=""
                  className={`size-3 ${remainingUnread.length > 0 ? "invert brightness-0" : ""}`}
                  src={imgEdit}
                />
                {remainingUnread.length > 0
                  ? `Type unread fields (${remainingUnread.length})`
                  : "Edit"}
              </Link>

              {/* Building a plan is impossible while a required field remains unread or flagged field is unresolved */}
              {remainingUnread.length > 0 ? (
                <div className="mt-2">
                  <button
                    type="button"
                    disabled
                    aria-disabled="true"
                    className="flex h-[40px] w-full items-center justify-center rounded-lg bg-zinc-200 text-[14px] font-bold text-zinc-400 cursor-not-allowed"
                  >
                    Confirm (fill unread fields first)
                  </button>
                  <p className="mt-1.5 text-center text-[11px] text-rose-600 font-medium">
                    Building a plan is impossible while required fields remain unread.
                  </p>
                </div>
              ) : unresolvedFlagged.length > 0 ? (
                <div className="mt-2">
                  <button
                    type="button"
                    disabled
                    aria-disabled="true"
                    className="flex h-[40px] w-full items-center justify-center rounded-lg bg-zinc-200 text-[14px] font-bold text-zinc-400 cursor-not-allowed"
                  >
                    Confirm ({unresolvedFlagged.length} flagged {unresolvedFlagged.length === 1 ? "field" : "fields"} to verify)
                  </button>
                  <p className="mt-1.5 text-center text-[11px] text-amber-700 font-medium">
                    Building a plan is impossible while a flagged field is unresolved.
                  </p>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="mt-2 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white shadow-sm hover:bg-[#0e6353]"
                >
                  Confirm
                </button>
              )}
            </div>
          </>
        ) : (
          <div className="mx-[30px] mt-[18px] rounded-[15px] bg-white p-[25px] text-center text-zinc-600 shadow-sm border border-black/5">
            <p className="text-[13px]">No InBody reading data available.</p>
            <Link
              href="/upload"
              className="mt-4 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white shadow-sm"
            >
              ← Return to Gallery
            </Link>
          </div>
        )}
      </div>
    </PhoneFrame>
  );
}
