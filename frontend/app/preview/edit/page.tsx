"use client";

// Edit — built to Figma frame "Edit" (node 2059:1312).

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import { EditedMarker, FlagDot, FlagMarker, MarkerLegend, NoteBubble } from "@/components/FieldStatus";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, Modal } from "@/components/ui";
import { API_URL } from "@/lib/config";
import {
  FIELD_CONSTRAINTS,
  getFieldLabel,
  normalizeFieldKey,
  parseAndValidateFieldInput,
  validateFieldValue,
} from "@/lib/corrections";
import {
  BMR_FIELD,
  BODY_COMPOSITION_FIELDS,
  DEFAULT_READING,
  SEGMENTAL_LEAN_COLUMNS,
  blankRequiredFields,
  type InBodyDraft,
  type InBodyPayload,
  type SampleExtraction,
  type ScalarInBodyField,
  type SegmentalLeanField,
} from "@/lib/inbody";
import { loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "@/lib/session";

/** Visceral Fat Level is the one optional field (ADR-0004). */
const OPTIONAL_FIELD_KEYS = new Set(["visceral_fat_level"]);

const UNREAD_MESSAGE = "We couldn't read this number. Please type it in from your InBody report.";

function isSegmentField(key: string): key is SegmentalLeanField {
  return (
    key === "left_arm_kg" ||
    key === "right_arm_kg" ||
    key === "left_leg_kg" ||
    key === "right_leg_kg" ||
    key === "trunk_kg"
  );
}

type EditableField = {
  normKey: string;
  inputKey: string;
  label: string;
  unit: string;
  value: number | null;
  optional: boolean;
};

const inputId = (normKey: string) => `field-${normKey.replace(/\./g, "-")}`;

/**
 * The value box. Every box on the page is exactly this size (64x22), whatever
 * the field, so the column lines up (Figma: 0.8px rgba(217,217,217,0.7) border, 5px radius).
 */
function ValueBox({
  value,
  fieldKey,
  normKey,
  label,
  unit,
  invalid,
  describedBy,
  onFieldChange,
}: {
  value: number | null;
  fieldKey: string;
  normKey: string;
  label: string;
  unit: string;
  invalid: boolean;
  describedBy?: string;
  onFieldChange: (val: number | null, unit?: string, error?: string | null) => void;
}) {
  const [typedText, setTypedText] = useState<string | null>(null);
  const displayValue = typedText !== null ? typedText : value != null ? String(value) : "";

  return (
    <span
      className={`flex h-[22px] w-[64px] shrink-0 items-center justify-end gap-[3px] rounded-[5px] border-[0.8px] px-[6px] focus-within:border-[#fcfcfc] ${
        invalid ? "border-[#5cbfa8] ring-1 ring-[#5cbfa8]" : "border-[rgba(217,217,217,0.7)]"
      }`}
    >
      <input
        id={inputId(normKey)}
        type="text"
        inputMode="decimal"
        value={displayValue}
        placeholder="—"
        aria-label={label}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        onChange={(e) => {
          setTypedText(e.target.value);
          const r = parseAndValidateFieldInput(fieldKey, e.target.value);
          onFieldChange(r.value, r.unit, r.error);
        }}
        onBlur={() => {
          if (typedText !== null && !parseAndValidateFieldInput(fieldKey, typedText).error) setTypedText(null);
        }}
        className="w-full min-w-0 bg-transparent text-right text-[12px] font-bold text-[#fcfcfc] outline-none placeholder:text-white/40"
      />
      {unit && <span className="shrink-0 text-[8px] font-medium leading-none text-[#fcfcfc]">{unit}</span>}
    </span>
  );
}

export default function PreviewEdit() {
  const router = useRouter();
  const [draft, setDraft] = useState<InBodyDraft>(DEFAULT_READING);
  const [photo, setPhoto] = useState<string | null>(null);
  const [viewingPhoto, setViewingPhoto] = useState(false);
  const [corrections, setCorrections] = useState<Record<string, { value: number; unit?: string }>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});
  const [unreadKeys, setUnreadKeys] = useState<Set<string>>(new Set());
  const [flaggedKeys, setFlaggedKeys] = useState<Set<string>>(new Set());
  const [extraction, setExtraction] = useState<SampleExtraction | null>(null);
  const [showErrors, setShowErrors] = useState(false);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    const storedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);
    const storedCorrections =
      loadJSON<Record<string, { value: number; unit?: string }>>(SESSION_KEYS.corrections) ?? {};
    const loadedExtraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);
    const loadedSampleId = loadJSON<string>(SESSION_KEYS.sampleId);

    /* eslint-disable react-hooks/set-state-in-effect */
    setExtraction(loadedExtraction);
    setCorrections(storedCorrections);
    setPhoto(loadedSampleId ? `${API_URL}/samples/${loadedSampleId}/image` : loadJSON<string>(SESSION_KEYS.photo));
    if (loadedExtraction?.flagged) setFlaggedKeys(new Set(loadedExtraction.flagged.map(normalizeFieldKey)));

    const source = storedReading ?? loadedExtraction?.data ?? DEFAULT_READING;
    const base: InBodyDraft = { ...source, segmental_lean: { ...source.segmental_lean } };

    // An unread field has no value and must not be pre-filled with a made-up one (ADR-0008).
    if (loadedExtraction?.unread && loadedExtraction.unread.length > 0) {
      const unreadSet = new Set(loadedExtraction.unread.map(normalizeFieldKey));
      setUnreadKeys(unreadSet);
      const scalars: ScalarInBodyField[] = [
        "weight_kg",
        "lean_body_mass_kg",
        "percent_body_fat",
        "skeletal_muscle_mass_kg",
        "visceral_fat_level",
        "basal_metabolic_rate_kcal",
      ];
      for (const f of scalars) if (unreadSet.has(f) && !(f in storedCorrections)) base[f] = null;
      const segments: SegmentalLeanField[] = ["left_arm_kg", "right_arm_kg", "left_leg_kg", "right_leg_kg", "trunk_kg"];
      for (const f of segments) {
        const nk = normalizeFieldKey(f);
        if (unreadSet.has(nk) && !(nk in storedCorrections) && !(f in storedCorrections) && base.segmental_lean) {
          base.segmental_lean[f] = null;
        }
      }
    }

    // Re-apply corrections typed on an earlier visit.
    for (const [rawKey, corr] of Object.entries(storedCorrections)) {
      const nk = normalizeFieldKey(rawKey);
      const val = typeof corr === "object" && corr !== null && "value" in corr ? corr.value : Number(corr);
      if (Number.isNaN(val)) continue;
      if (isSegmentField(rawKey)) {
        if (base.segmental_lean) base.segmental_lean[rawKey] = val;
      } else if (nk.startsWith("segmental_lean.")) {
        if (base.segmental_lean) base.segmental_lean[nk.replace("segmental_lean.", "") as SegmentalLeanField] = val;
      } else if (rawKey in base) {
        (base as Record<string, unknown>)[rawKey] = val;
      }
    }
    setDraft(base);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const updateField = (key: string, value: number | null, unit?: string, error?: string | null) => {
    if (isSegmentField(key)) {
      setDraft((p) => ({ ...p, segmental_lean: { ...p.segmental_lean, [key]: value } }));
    } else {
      setDraft((p) => ({ ...p, [key as ScalarInBodyField]: value }));
    }
    const normKey = normalizeFieldKey(key);
    const resolvedUnit = unit ?? FIELD_CONSTRAINTS[normKey]?.unit;
    if (error !== undefined) setFieldErrors((p) => ({ ...p, [normKey]: error }));

    // A typed value is a correction, recorded alongside the measured one, never merged.
    setCorrections((prev) => {
      const next = { ...prev };
      if (value !== null) next[normKey] = { value, ...(resolvedUnit ? { unit: resolvedUnit } : {}) };
      else {
        delete next[normKey];
        delete next[key];
      }
      saveJSON(SESSION_KEYS.corrections, next);
      return next;
    });
  };

  const field = (key: string, label: string, unit: string, value: number | null, optional = false): EditableField => ({
    normKey: normalizeFieldKey(key),
    inputKey: key,
    label,
    unit,
    value,
    optional,
  });

  const bodyFields = BODY_COMPOSITION_FIELDS.map((f) =>
    field(f.key, f.label, f.key === "visceral_fat_level" ? "level" : f.unit, draft[f.key], OPTIONAL_FIELD_KEYS.has(f.key)),
  );
  const segmentColumns = SEGMENTAL_LEAN_COLUMNS.map((col) =>
    col.map((f) => field(f.key, f.label, f.unit, draft.segmental_lean?.[f.key] ?? null)),
  );
  const bmrField = field(BMR_FIELD.key, BMR_FIELD.label, BMR_FIELD.unit, draft[BMR_FIELD.key]);
  const allFields = [...bodyFields, ...segmentColumns.flat(), bmrField];

  const isCorrected = (normKey: string) => normKey in corrections;
  const blank = blankRequiredFields(draft);

  // The reason each value can't be accepted yet, if any. Shown under that value.
  const problemFor = (f: EditableField): string | null => {
    const typed = fieldErrors[f.normKey];
    if (typed) return typed;
    const range = f.value !== null ? validateFieldValue(f.normKey, f.value) : null;
    if (range) return range;
    if (
      f.normKey === "lean_body_mass_kg" &&
      draft.weight_kg != null &&
      draft.lean_body_mass_kg != null &&
      draft.lean_body_mass_kg > draft.weight_kg
    ) {
      return "Lean Body Mass can't be more than your Weight. Check both against your report.";
    }
    if (f.value === null && !f.optional && showErrors) {
      return "This number is needed for your plan. Type it in from your InBody report.";
    }
    return null;
  };

  const problems = allFields
    .map((f) => ({ f, message: problemFor(f) }))
    .filter((p): p is { f: EditableField; message: string } => p.message !== null);
  const canSubmit = blank.length === 0 && problems.length === 0;

  // Flagged fields left as read: saving records them as checked by the person.
  const reviewedUnchanged = [...flaggedKeys].filter((nk) => !isCorrected(nk));

  const handleSave = () => {
    if (!canSubmit) {
      setShowErrors(true);
      // Take the person straight to the first value that needs fixing.
      const first =
        problems[0]?.f ?? allFields.find((f) => f.value === null && !f.optional) ?? null;
      if (first) {
        const el = document.getElementById(inputId(first.normKey));
        el?.scrollIntoView({ block: "center", behavior: "smooth" });
        el?.focus({ preventScroll: true });
      }
      return;
    }
    saveJSON(SESSION_KEYS.reading, draft);
    if (extraction?.data) saveJSON(SESSION_KEYS.measured, extraction.data);
    if (Object.keys(corrections).length > 0) saveJSON(SESSION_KEYS.corrections, corrections);
    else removeSessionItem(SESSION_KEYS.corrections);
    if (reviewedUnchanged.length > 0) saveJSON(SESSION_KEYS.confirmations, reviewedUnchanged);
    else removeSessionItem(SESSION_KEYS.confirmations);
    router.push("/preview");
  };

  /** One parameter row: label, status marker, value box, and (if needed) the bubble. */
  const renderRow = (f: EditableField, bubbleAlign: "left" | "right" = "right") => {
    const problem = problemFor(f);
    const noteId = problem ? `${inputId(f.normKey)}-note` : undefined;
    const isUnread = unreadKeys.has(f.normKey) && f.value === null;
    const marker = problem ? (
      <FlagDot />
    ) : isCorrected(f.normKey) ? (
      <EditedMarker />
    ) : isUnread ? (
      <FlagMarker label={f.label} message={UNREAD_MESSAGE} align={bubbleAlign} />
    ) : flaggedKeys.has(f.normKey) ? (
      <FlagMarker label={f.label} align={bubbleAlign} />
    ) : null;

    return (
      <div key={f.normKey}>
        <div className="flex h-[24px] items-center gap-[8px]">
          <label htmlFor={inputId(f.normKey)} className="min-w-0 flex-1 truncate text-[12px] text-[#fcfcfc]">
            {f.label}
          </label>
          <span className="flex w-[16px] shrink-0 justify-center">{marker}</span>
          <ValueBox
            value={f.value}
            fieldKey={f.inputKey}
            normKey={f.normKey}
            label={f.label}
            unit={f.unit}
            invalid={problem !== null}
            describedBy={noteId}
            onFieldChange={(v, u, e) => updateField(f.inputKey, v, u, e)}
          />
        </div>
        {problem && <NoteBubble id={noteId}>{problem}</NoteBubble>}
      </div>
    );
  };

  const hasEdited = allFields.some((f) => isCorrected(f.normKey));
  const problemLabels = [...new Set([...problems.map((p) => p.f.label), ...blank])];

  return (
    <PhoneFrame bg="bg-gradient-to-b from-[#3e3e3e] to-[#222]">
      {/* Sheet photo header */}
      <div className="relative h-[275px] w-full overflow-hidden">
        {photo && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            alt=""
            src={photo}
            className="size-full object-cover object-top"
            onError={(e) => {
              e.currentTarget.style.visibility = "hidden";
            }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-[#3e3e3e] from-[7%] to-[rgba(62,62,62,0.3)]" />
        <BackButton href="/preview" label="Back to the preview" screenAligned />
        {photo && (
          <button
            type="button"
            onClick={() => setViewingPhoto(true)}
            aria-label="View the full sheet photo"
            className="absolute right-[30px] top-[48px] flex size-[24px] items-center justify-center rounded-full bg-[#117d69] text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            <Icon name="eye" size={14} />
          </button>
        )}
        <div className="absolute inset-x-[30px] bottom-[20px] text-[#fcfcfc]">
          <h1 className="text-[24px] font-bold">Edit</h1>
          <p className="mt-[5px] text-[12px] leading-[1.5] tracking-[0.02em]">
            Make sure the flagged numbers match your InBody report.
          </p>
        </div>
      </div>

      <div className="px-[30px] pb-[48px] pt-[12px] text-[#fcfcfc]">
        <h2 className="text-[16px] font-bold">Body Composition</h2>
        <div className="mt-[8px]">{bodyFields.map((f) => renderRow(f))}</div>

        <div className="my-[24px] border-t border-dotted border-[#fcfcfc]/60" aria-hidden="true" />

        <h2 className="text-[16px] font-bold">Segmental Lean Analysis</h2>
        <div className="mt-[8px] grid grid-cols-2 gap-x-[16px]">
          {segmentColumns.map((col, i) => (
            <div key={i}>{col.map((f) => renderRow(f, i === 0 ? "left" : "right"))}</div>
          ))}
        </div>

        <div className="my-[24px] border-t border-dotted border-[#fcfcfc]/60" aria-hidden="true" />

        <div className="[&_label]:text-[14px] [&_label]:font-bold">{renderRow(bmrField)}</div>

        <MarkerLegend edited={hasEdited} checked={false} />

        {showErrors && problemLabels.length > 0 && (
          <p role="alert" className="mt-[24px] text-center text-[11px] leading-[1.5] text-[#fcfcfc]/80">
            Fix {problemLabels.length === 1 ? "this value" : "these values"} to continue:{" "}
            <strong>{problemLabels.join(", ")}</strong>
          </p>
        )}

        <button type="button" onClick={handleSave} className={`${btn.primary} mt-[24px]`}>
          Save
        </button>
        {reviewedUnchanged.length > 0 && (
          <p className="mt-[8px] text-center text-[10px] leading-relaxed text-white/60">
            Saving records {reviewedUnchanged.map(getFieldLabel).join(", ")} as checked by you.
          </p>
        )}
      </div>

      <Modal open={viewingPhoto} onClose={() => setViewingPhoto(false)} title="Your sheet" widthClass="max-w-[370px]">
        {photo && (
          // eslint-disable-next-line @next/next/no-img-element
          <img alt="The InBody sheet these numbers were read from" src={photo} className="mt-3 w-full rounded-[8px]" />
        )}
        <button type="button" onClick={() => setViewingPhoto(false)} className={`${btn.secondary} mt-4`}>
          Close
        </button>
      </Modal>
    </PhoneFrame>
  );
}
