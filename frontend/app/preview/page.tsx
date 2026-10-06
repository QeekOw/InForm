"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, cardClass, Modal, Tag } from "@/components/ui";
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
import { loadJSON, SESSION_KEYS } from "@/lib/session";

type RowStatus = "unread" | "flagged" | "confirmed" | "corrected" | null;

function statusOf(opts: {
  isUnread: boolean;
  isFlagged: boolean;
  isCorrected: boolean;
  isConfirmed: boolean;
}): RowStatus {
  if (opts.isCorrected) return "corrected";
  if (opts.isUnread) return "unread";
  if (opts.isFlagged && !opts.isConfirmed) return "flagged";
  if (opts.isFlagged && opts.isConfirmed) return "confirmed";
  return null;
}

/**
 * One extracted value on the dark review screen, labelled with how much to
 * trust it. Read-only: a single Edit action deals with every flagged and unread
 * value at once (the fail-closed gate is satisfied by one submit there).
 */
function Row({ label, value, unit, status }: { label: string; value: string | number | null; unit: string; status: RowStatus }) {
  const tag =
    status === "unread" ? (
      <Tag tone="rose">Couldn&apos;t read</Tag>
    ) : status === "flagged" ? (
      <Tag tone="amber">
        <Icon name="alert" size={9} className="mr-[2px]" />
        Check this
      </Tag>
    ) : status === "confirmed" ? (
      <Tag tone="teal">Checked</Tag>
    ) : status === "corrected" ? (
      <Tag tone="sky">Edited</Tag>
    ) : null;

  return (
    <div
      className={`flex items-center justify-between gap-2 py-[4px] text-[12px] ${
        status === "flagged" || status === "unread" ? "-mx-[8px] rounded-[6px] bg-amber-400/10 px-[8px]" : ""
      }`}
    >
      <span className="flex min-w-0 items-center gap-[6px]">
        <span className="truncate">{label}</span>
        {tag}
      </span>
      <span className="shrink-0 font-bold">
        {value ?? "—"}
        {value != null && unit && <span className="ml-[3px] text-[9px] font-medium opacity-80">{unit}</span>}
      </span>
    </div>
  );
}

/** The sheet photo across the top of the screen, faded into the background. */
function PhotoHeader({ src, height, onView }: { src: string | null; height: number; onView?: () => void }) {
  return (
    <div className="relative w-full overflow-hidden" style={{ height }}>
      {src && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt=""
          src={src}
          className="size-full object-cover object-top"
          onError={(e) => {
            e.currentTarget.style.visibility = "hidden";
          }}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-[#3e3e3e]/40 to-[#3e3e3e]" />
      <BackButton href="/upload" className="absolute left-[31px] top-[48px]" />
      {src && onView && (
        <button
          type="button"
          onClick={onView}
          aria-label="View the full sheet photo"
          className="absolute right-[30px] top-[48px] flex size-[28px] items-center justify-center rounded-full bg-[#117d69] text-white shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
        >
          <Icon name="eye" size={15} />
        </button>
      )}
    </div>
  );
}

export default function Preview() {
  const router = useRouter();
  const [reading, setReading] = useState<InBodyPayload | null>(null);
  const [extraction, setExtraction] = useState<SampleExtraction | null>(null);
  const [sampleId, setSampleId] = useState<string | null>(null);
  const [photo, setPhoto] = useState<string | null>(null);
  const [corrections, setCorrections] = useState<Record<string, unknown>>({});
  const [confirmedFields, setConfirmedFields] = useState<Set<string>>(new Set());
  const [viewingPhoto, setViewingPhoto] = useState(false);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    const loadedExtraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);
    const loadedSampleId = loadJSON<string>(SESSION_KEYS.sampleId);
    const storedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);
    const storedCorrections = loadJSON<Record<string, unknown>>(SESSION_KEYS.corrections) ?? {};
    const storedConfirmations = loadJSON<string[]>(SESSION_KEYS.confirmations) ?? [];

    /* eslint-disable react-hooks/set-state-in-effect */
    setExtraction(loadedExtraction);
    setSampleId(loadedSampleId);
    setPhoto(
      loadedSampleId ? `${API_URL}/samples/${loadedSampleId}/image` : loadJSON<string>(SESSION_KEYS.photo),
    );
    setCorrections(storedCorrections);
    setConfirmedFields(new Set(storedConfirmations.map(normalizeFieldKey)));

    // Hard refuse on non-InBody documents or zero-read floor cases (ADR-0008 Amendment §3)
    const isHardRefusalCase =
      loadedExtraction?.error === "not_an_inbody_sheet" ||
      (loadedExtraction?.status === "refused" && loadedExtraction?.data == null);

    if (isHardRefusalCase) setReading(null);
    else if (storedReading) setReading(storedReading);
    else if (loadedExtraction?.data) setReading(loadedExtraction.data);
    else setReading(DEFAULT_READING);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  // The model isn't installed on this server (ADR-0010). Checked first so a
  // server-side fact is never presented as a problem with the person's photo.
  const isEngineUnavailable = extraction?.error === "engine_unavailable";
  const isNotAnInBodySheet =
    !isEngineUnavailable &&
    (extraction?.error === "not_an_inbody_sheet" ||
      (extraction?.message?.toLowerCase().includes("not appear to be an inbody") ?? false));
  const isRefusedSheet =
    !isEngineUnavailable &&
    !isNotAnInBodySheet &&
    (extraction?.status === "refused" ||
      (reading === null && extraction !== null && extraction?.data == null));

  const flaggedFields = new Set((extraction?.flagged ?? []).map(normalizeFieldKey));
  const unreadFromExtraction = new Set((extraction?.unread ?? []).map(normalizeFieldKey));
  const correctedFields = new Set(Object.keys(corrections).map(normalizeFieldKey));
  const unresolvedFlagged = getUnresolvedFlagged(extraction?.flagged, corrections, confirmedFields);

  const remainingUnread: string[] = [];
  if (reading) {
    for (const key of [
      "weight_kg",
      "lean_body_mass_kg",
      "percent_body_fat",
      "skeletal_muscle_mass_kg",
      "basal_metabolic_rate_kcal",
    ] as const) {
      if (reading[key] == null) remainingUnread.push(key);
    }
    if (reading.segmental_lean) {
      for (const key of ["left_arm_kg", "right_arm_kg", "left_leg_kg", "right_leg_kg", "trunk_kg"] as const) {
        if (reading.segmental_lean[key] == null) remainingUnread.push(`segmental_lean.${key}`);
      }
    }
  }

  // Everything still needing a person, counted once.
  const reviewCount = remainingUnread.length + unresolvedFlagged.length;
  const needsReview = reviewCount > 0;
  const isDemoReading =
    !sampleId && reading !== null && JSON.stringify(reading) === JSON.stringify(DEFAULT_READING);

  const handleConfirm = () => {
    if (reading && !needsReview) {
      router.push(
        confirmReading(reading, corrections as Record<string, number>, extraction?.data, Array.from(confirmedFields)),
      );
    }
  };

  const status = (key: string, value: unknown) =>
    statusOf({
      isUnread: value == null || unreadFromExtraction.has(key),
      isFlagged: flaggedFields.has(key),
      isCorrected: correctedFields.has(key),
      isConfirmed: confirmedFields.has(key),
    });

  const photoModal = (
    <Modal open={viewingPhoto} onClose={() => setViewingPhoto(false)} title="Your sheet" widthClass="max-w-[370px]">
      {photo && (
        // eslint-disable-next-line @next/next/no-img-element
        <img alt="The InBody sheet these numbers were read from" src={photo} className="mt-3 w-full rounded-[8px]" />
      )}
      <button type="button" onClick={() => setViewingPhoto(false)} className={`${btn.secondary} mt-4`}>
        <Icon name="close" size={16} />
        Close
      </button>
    </Modal>
  );

  // --- Couldn't read (three honest variants) --------------------------------
  if (isEngineUnavailable || isNotAnInBodySheet || isRefusedSheet) {
    const title = isEngineUnavailable
      ? "Reading isn't available right now"
      : isNotAnInBodySheet
        ? "This doesn't look like an InBody report"
        : "We failed to read your report";
    const body = isEngineUnavailable
      ? "The part of InForm that reads sheets isn't installed on this server. This isn't a problem with your photo, and retaking it won't help. The sample sheets still work."
      : isNotAnInBodySheet
        ? "We couldn't find InBody results in this image. Please use a clear photo of an InBody 270 sheet."
        : sampleId
          ? "We couldn't read the numbers on this sheet clearly enough. Rather than guess, we'd like you to pick another one."
          : "Something went wrong while reading your InBody report. Please make sure the photo is clear, complete, and easy to read, then try again.";

    return (
      <PhoneFrame bg="bg-[#3e3e3e]">
        <PhotoHeader src={photo} height={433} />
        <div className="relative -mt-[0px] px-[30px] pb-[48px] text-[#fcfcfc]">
          <h1 className="text-[24px] font-bold leading-tight tracking-[0.02em]">{title}</h1>
          <p className="mt-[5px] text-[12px] leading-[1.5] text-[#fcfcfc]/90">{body}</p>

          {!isEngineUnavailable && !sampleId && (
            <div className={`${cardClass} mt-[32px] p-[16px] text-[12px]`}>
              <p className="flex items-center gap-[7px] font-bold text-[#117d69]">
                <Icon name="bulb" size={16} />
                Tips for a better scan
              </p>
              <ul className="mt-[6px] list-disc space-y-[2px] pl-[22px] text-[11px] text-black/75">
                <li>Make sure all text and numbers are visible</li>
                <li>Avoid blurry or dark photos</li>
                <li>Keep the report flat and fully inside the frame</li>
              </ul>
            </div>
          )}

          <div className="mt-[42px] space-y-[15px]">
            {!isEngineUnavailable && !sampleId && (
              <div className="flex gap-[15px]">
                <Link href="/upload/capture" className={`${btn.light} text-black`}>
                  <Icon name="camera" size={16} className="text-[#117d69]" />
                  Retake
                </Link>
                <Link href="/upload" className={`${btn.light} text-black`}>
                  <Icon name="image" size={16} className="text-[#117d69]" />
                  Open Files
                </Link>
              </div>
            )}
            <Link href="/upload" className={btn.primary}>
              {isEngineUnavailable ? "Use a sample sheet instead" : sampleId ? "Choose another sheet" : "Try Again"}
              <Icon name="arrowRight" size={16} />
            </Link>
          </div>
        </div>
      </PhoneFrame>
    );
  }

  if (!reading || !reading.segmental_lean) {
    return (
      <PhoneFrame bg="bg-[#3e3e3e]">
        <PhotoHeader src={null} height={175} />
        <div className="px-[30px] text-center text-[#fcfcfc]">
          <p className="text-[13px]">No InBody reading to show.</p>
          <Link href="/upload" className={`${btn.primary} mt-4`}>
            Pick a sheet
          </Link>
        </div>
      </PhoneFrame>
    );
  }

  // --- Review -----------------------------------------------------------------
  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <PhotoHeader src={photo} height={275} onView={() => setViewingPhoto(true)} />

      <div className="relative -mt-[90px] px-[30px] pb-[48px] text-[#fcfcfc]">
        <h1 className="text-[24px] font-bold tracking-[0.02em]">Report scanned successfully</h1>
        <p className="mt-[5px] text-[12px] leading-[1.5] text-[#fcfcfc]/90">
          Please review the extracted information below and make sure all details are correct
          before continuing.
        </p>

        {isDemoReading && (
          <p className="mt-3 rounded-[8px] bg-white/10 px-3 py-1.5 text-[11px] text-white/80">
            These are demo baseline values, not a reading of a sheet. Edit them before continuing.
          </p>
        )}

        {needsReview ? (
          <div role="status" className="mt-[16px] rounded-[8px] border border-amber-300/50 bg-amber-400/15 p-[10px] text-[11px] leading-relaxed text-amber-100">
            <p className="flex items-center gap-[6px] font-bold">
              <Icon name="alert" size={13} />
              {reviewCount === 1 ? "One number needs a quick check" : `${reviewCount} numbers need a quick check`}
            </p>
            {remainingUnread.length > 0 && (
              <p className="mt-1">
                <span className="font-semibold">We couldn&apos;t read:</span>{" "}
                {remainingUnread.map(getFieldLabel).join(", ")}. Type these in from your sheet.
              </p>
            )}
            {unresolvedFlagged.length > 0 && (
              <p className="mt-1">
                <span className="font-semibold">These don&apos;t quite add up:</span>{" "}
                {unresolvedFlagged.map(getFieldLabel).join(", ")}. One of them was probably misread.
                Compare them with your sheet.
              </p>
            )}
          </div>
        ) : flaggedFields.size > 0 || correctedFields.size > 0 ? (
          <p role="status" className="mt-[16px] rounded-[8px] bg-[#117d69]/25 p-[10px] text-[11px] text-[#d6f5ef]">
            <span className="font-bold">All checked.</span> Everything doubtful has been edited or
            confirmed against your sheet.
          </p>
        ) : null}

        <h2 className="mt-[28px] text-[16px] font-bold">Body Composition</h2>
        <div className="mt-[8px]">
          {BODY_COMPOSITION_FIELDS.map((field) => {
            const value = reading[field.key];
            return (
              <Row
                key={field.key}
                label={field.label}
                value={value != null && field.formatValue ? field.formatValue(value) : value}
                unit={field.key === "visceral_fat_level" ? "level" : field.unit}
                status={status(field.key, value)}
              />
            );
          })}
        </div>

        <div className="my-[22px] h-px bg-[#fcfcfc]/30" />

        <h2 className="text-[16px] font-bold">Segmental Lean Analysis</h2>
        <div className="mt-[8px] grid grid-cols-2 gap-x-[24px]">
          {SEGMENTAL_LEAN_COLUMNS.map((column) => (
            <div key={column[0].key}>
              {column.map((field) => {
                const dottedKey = `segmental_lean.${field.key}`;
                const value = reading.segmental_lean[field.key];
                return (
                  <Row key={field.key} label={field.label} value={value} unit={field.unit} status={status(dottedKey, value)} />
                );
              })}
            </div>
          ))}
        </div>

        <div className="my-[22px] h-px bg-[#fcfcfc]/30" />

        <Row
          label={BMR_FIELD.label}
          value={reading[BMR_FIELD.key]}
          unit={BMR_FIELD.unit}
          status={status(BMR_FIELD.key, reading[BMR_FIELD.key])}
        />

        {/* One action resolves every flagged and unread field on one page. */}
        <Link
          href="/preview/edit"
          className={`${needsReview ? btn.primary : `${btn.light} text-black`} mt-[48px]`}
        >
          <Icon name="pencil" size={14} className={needsReview ? "" : "text-[#117d69]"} />
          {needsReview ? `Check & fix (${reviewCount})` : "Edit"}
        </Link>

        {/* The fail-closed gate (issue #39, ADR-0008): a flagged or unread
            value still blocks the plan outright. */}
        <button
          type="button"
          onClick={handleConfirm}
          disabled={needsReview}
          aria-describedby={needsReview ? "confirm-blocked" : undefined}
          className={`${needsReview ? btn.secondary : btn.primary} mt-[15px]`}
        >
          Confirm
        </button>
        {needsReview && (
          <p id="confirm-blocked" className="mt-[6px] text-center text-[11px] font-medium text-amber-200">
            {remainingUnread.length > 0
              ? "Your plan needs every number, so fill in the missing ones first."
              : "Check the flagged numbers first, so your plan isn't built on a misread."}
          </p>
        )}
      </div>
      {photoModal}
    </PhoneFrame>
  );
}
