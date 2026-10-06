"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, Modal, Tag } from "@/components/ui";
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

function isSegmentField(key: string): key is SegmentalLeanField {
  return (
    key === "left_arm_kg" ||
    key === "right_arm_kg" ||
    key === "left_leg_kg" ||
    key === "right_leg_kg" ||
    key === "trunk_kg"
  );
}

/** One editable value, flattened out of the three separate groups the sheet is
 * displayed in, so flagged and unread fields from anywhere on the sheet can be
 * gathered onto one list (Requirement 4.3). */
type EditableField = {
  /** Canonical dotted key, e.g. `segmental_lean.left_arm_kg`. */
  normKey: string;
  /** The key `updateField` expects: short for segments, plain for scalars. */
  inputKey: string;
  label: string;
  unit: string;
  value: number | null;
  optional: boolean;
};

function ValueField({
  value,
  fieldKey,
  label,
  unit,
  invalid = false,
  onFieldChange,
}: {
  value: number | null;
  fieldKey: string;
  /** Accessible name for the input. */
  label: string;
  unit: string;
  invalid?: boolean;
  onFieldChange: (val: number | null, unit?: string, error?: string | null) => void;
}) {
  const [typedText, setTypedText] = useState<string | null>(null);

  const displayValue = typedText !== null ? typedText : value != null ? String(value) : "";

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    setTypedText(raw);
    const result = parseAndValidateFieldInput(fieldKey, raw);
    onFieldChange(result.value, result.unit, result.error);
  };

  const handleBlur = () => {
    if (typedText !== null) {
      const result = parseAndValidateFieldInput(fieldKey, typedText);
      if (!result.error) {
        setTypedText(null);
      }
    }
  };

  return (
    <span
      className={`flex h-[24px] items-center gap-1 rounded-[6px] bg-[#fcfcfc] px-2 text-black focus-within:ring-2 focus-within:ring-[#7ee0cf] ${
        invalid ? "ring-2 ring-rose-400" : ""
      }`}
    >
      <input
        type="text"
        inputMode="decimal"
        value={displayValue}
        placeholder="—"
        aria-invalid={invalid}
        aria-label={label}
        onBlur={handleBlur}
        onChange={handleChange}
        className="w-[52px] bg-transparent text-right text-[12px] font-bold outline-none"
      />
      {unit && <span className="text-[9px] font-medium opacity-60">{unit}</span>}
    </span>
  );
}

/**
 * One row: label, the reason it needs attention, an input, and any error.
 *
 * No Confirm/Undo button. A flagged value left unchanged is reviewed by
 * submitting this page, which is one act covering every flagged field at once
 * (Requirements 4.2, 4.4). The gate itself is untouched: submitting is still
 * the thing that has to happen before a plan exists (issue #39, ADR-0008).
 */
function Row({
  label,
  fieldKey,
  value,
  unit,
  onChange,
  invalid = false,
  isUnread = false,
  isFlagged = false,
  isCorrected = false,
  optional = false,
  error = null,
}: {
  label: string;
  fieldKey: string;
  value: number | null;
  unit: string;
  onChange: (v: number | null, unit?: string, error?: string | null) => void;
  invalid?: boolean;
  isUnread?: boolean;
  isFlagged?: boolean;
  isCorrected?: boolean;
  optional?: boolean;
  error?: string | null;
}) {
  return (
    <div className="py-[3px]">
      <div className="flex items-center justify-between gap-2 text-[12px]">
        <span className="flex min-w-0 flex-wrap items-center gap-1.5">
          <span>{label}</span>
          {optional && <span className="text-[9px] text-white/50">optional</span>}
          {isUnread && !isCorrected && <Tag tone="rose">Couldn&apos;t read</Tag>}
          {isFlagged && !isCorrected && (
            <Tag tone="amber">
              <Icon name="alert" size={9} className="mr-[2px]" />
              Check this
            </Tag>
          )}
          {isCorrected && <Tag tone="sky">Edited</Tag>}
        </span>
        <ValueField
          value={value}
          fieldKey={fieldKey}
          label={label}
          unit={unit}
          invalid={invalid}
          onFieldChange={onChange}
        />
      </div>
      {error && (
        <p role="alert" className="mt-0.5 text-right text-[10px] font-medium text-rose-300">
          {error}
        </p>
      )}
    </div>
  );
}

export default function PreviewEdit() {
  const router = useRouter();
  const [draft, setDraft] = useState<InBodyDraft>(DEFAULT_READING);
  const [photo, setPhoto] = useState<string | null>(null);
  const [viewingPhoto, setViewingPhoto] = useState(false);
  const [corrections, setCorrections] = useState<Record<string, { value: number; unit?: string }>>(
    {},
  );
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});
  const [unreadKeys, setUnreadKeys] = useState<Set<string>>(new Set());
  const [flaggedKeys, setFlaggedKeys] = useState<Set<string>>(new Set());
  const [extraction, setExtraction] = useState<SampleExtraction | null>(null);
  const [showErrors, setShowErrors] = useState(false);
  const [showWholeSheet, setShowWholeSheet] = useState(false);

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
    setPhoto(
      loadedSampleId ? `${API_URL}/samples/${loadedSampleId}/image` : loadJSON<string>(SESSION_KEYS.photo),
    );

    if (loadedExtraction?.flagged) {
      setFlaggedKeys(new Set(loadedExtraction.flagged.map(normalizeFieldKey)));
    }

    const base: InBodyDraft = storedReading
      ? {
          ...storedReading,
          segmental_lean: { ...storedReading.segmental_lean },
        }
      : loadedExtraction?.data
        ? {
            ...loadedExtraction.data,
            segmental_lean: { ...loadedExtraction.data.segmental_lean },
          }
        : {
            ...DEFAULT_READING,
            segmental_lean: { ...DEFAULT_READING.segmental_lean },
          };

    // An unread field has no value, and must not be pre-filled with a demo or
    // default one — that would be handing someone a number to accept that nobody
    // measured (ADR-0008).
    if (loadedExtraction?.unread && loadedExtraction.unread.length > 0) {
      const unreadSet = new Set(loadedExtraction.unread.map(normalizeFieldKey));
      setUnreadKeys(unreadSet);

      const scalarFields: ScalarInBodyField[] = [
        "weight_kg",
        "lean_body_mass_kg",
        "percent_body_fat",
        "skeletal_muscle_mass_kg",
        "visceral_fat_level",
        "basal_metabolic_rate_kcal",
      ];
      for (const field of scalarFields) {
        if (unreadSet.has(field) && !(field in storedCorrections)) {
          base[field] = null;
        }
      }

      const segmentFields: SegmentalLeanField[] = [
        "left_arm_kg",
        "right_arm_kg",
        "left_leg_kg",
        "right_leg_kg",
        "trunk_kg",
      ];
      for (const field of segmentFields) {
        const normKey = normalizeFieldKey(field);
        if (
          unreadSet.has(normKey) &&
          !(normKey in storedCorrections) &&
          !(field in storedCorrections)
        ) {
          if (base.segmental_lean) {
            base.segmental_lean[field] = null;
          }
        }
      }
    }

    // Re-apply corrections typed on an earlier visit to this page.
    for (const [rawKey, corr] of Object.entries(storedCorrections)) {
      const normKey = normalizeFieldKey(rawKey);
      const val =
        typeof corr === "object" && corr !== null && "value" in corr ? corr.value : Number(corr);
      if (!Number.isNaN(val)) {
        if (isSegmentField(rawKey)) {
          if (base.segmental_lean) base.segmental_lean[rawKey] = val;
        } else if (normKey.startsWith("segmental_lean.")) {
          const segKey = normKey.replace("segmental_lean.", "") as SegmentalLeanField;
          if (base.segmental_lean) base.segmental_lean[segKey] = val;
        } else if (rawKey in base) {
          (base as Record<string, unknown>)[rawKey] = val;
        }
      }
    }

    setDraft(base);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const updateField = (
    key: string,
    value: number | null,
    unit?: string,
    error?: string | null,
  ) => {
    if (isSegmentField(key)) {
      setDraft((prev) => ({
        ...prev,
        segmental_lean: { ...prev.segmental_lean, [key]: value },
      }));
    } else {
      setDraft((prev) => ({ ...prev, [key as ScalarInBodyField]: value }));
    }

    const normKey = normalizeFieldKey(key);
    const resolvedUnit = unit ?? FIELD_CONSTRAINTS[normKey]?.unit;

    if (error !== undefined) {
      setFieldErrors((prev) => ({ ...prev, [normKey]: error }));
    }

    if (value !== null) {
      // A value a person typed is a corrected field, recorded alongside the
      // measured ones and never merged into them.
      setCorrections((prev) => {
        const next = {
          ...prev,
          [normKey]: { value, ...(resolvedUnit ? { unit: resolvedUnit } : {}) },
        };
        saveJSON(SESSION_KEYS.corrections, next);
        return next;
      });
    } else {
      setCorrections((prev) => {
        const next = { ...prev };
        delete next[normKey];
        delete next[key];
        saveJSON(SESSION_KEYS.corrections, next);
        return next;
      });
    }
  };

  const getFieldError = (normKey: string, value: number | null): string | null => {
    if (fieldErrors[normKey] !== undefined) {
      return fieldErrors[normKey];
    }
    return validateFieldValue(normKey, value);
  };

  // Every value on the sheet, flattened and in display order.
  const allFields: EditableField[] = [
    ...BODY_COMPOSITION_FIELDS.map((field) => ({
      normKey: normalizeFieldKey(field.key),
      inputKey: field.key as string,
      label: field.label,
      unit: field.key === "visceral_fat_level" ? "level" : field.unit,
      value: draft[field.key],
      optional: OPTIONAL_FIELD_KEYS.has(field.key),
    })),
    {
      normKey: normalizeFieldKey(BMR_FIELD.key),
      inputKey: BMR_FIELD.key as string,
      label: BMR_FIELD.label,
      unit: BMR_FIELD.unit,
      value: draft[BMR_FIELD.key],
      optional: false,
    },
    ...SEGMENTAL_LEAN_COLUMNS.flat().map((field) => ({
      normKey: normalizeFieldKey(field.key),
      inputKey: field.key as string,
      label: field.label,
      unit: field.unit,
      value: draft.segmental_lean?.[field.key] ?? null,
      optional: false,
    })),
  ];

  const errors: Record<string, string | null> = Object.fromEntries(
    allFields.map((field) => [field.normKey, getFieldError(field.normKey, field.value)]),
  );

  const isCorrected = (normKey: string) => normKey in corrections;

  // Everything the extraction couldn't read or couldn't reconcile, gathered from
  // all three groups onto one list (Requirement 4.3).
  const attentionFields = allFields.filter(
    (field) => unreadKeys.has(field.normKey) || flaggedKeys.has(field.normKey),
  );
  const otherFields = allFields.filter(
    (field) => !unreadKeys.has(field.normKey) && !flaggedKeys.has(field.normKey),
  );

  // Flagged fields the person has not retyped. Submitting the page records these
  // as reviewed: looked at, checked against the sheet, left as measured. They
  // stay measured fields and do not become corrections.
  const reviewedUnchanged = [...flaggedKeys].filter((normKey) => !isCorrected(normKey));

  let crossFieldError: string | null = null;
  if (
    draft.weight_kg != null &&
    draft.lean_body_mass_kg != null &&
    draft.lean_body_mass_kg > draft.weight_kg
  ) {
    crossFieldError = "Lean Body Mass can't be more than total Weight.";
  }

  const blank = blankRequiredFields(draft);
  const hasRangeErrors = Boolean(Object.values(errors).some(Boolean) || crossFieldError);

  // A value already on the sheet that sits outside its plausible range has to be
  // corrected — it cannot be accepted as-is (Requirement 4.7). This is what stops
  // the real_270_clean sample's misread 7 kg lean body mass from becoming a
  // 308 kcal daily target. The server's ImplausibleConfirmationError is the
  // backstop; this is the immediate answer.
  const outOfRangeFlagged = [...flaggedKeys].filter((normKey) => Boolean(errors[normKey]));

  const canSubmit = blank.length === 0 && !hasRangeErrors;

  /** Save corrections and the review of what was left unchanged, then return to
   * Preview, where Confirm builds the plan (Figma: Edit -> Save -> Preview). */
  const handleSave = () => {
    if (!canSubmit) {
      setShowErrors(true);
      return;
    }

    saveJSON(SESSION_KEYS.reading, draft);
    if (extraction?.data) {
      saveJSON(SESSION_KEYS.measured, extraction.data);
    }
    if (Object.keys(corrections).length > 0) {
      saveJSON(SESSION_KEYS.corrections, corrections);
    } else {
      removeSessionItem(SESSION_KEYS.corrections);
    }
    if (reviewedUnchanged.length > 0) {
      saveJSON(SESSION_KEYS.confirmations, reviewedUnchanged);
    } else {
      removeSessionItem(SESSION_KEYS.confirmations);
    }

    router.push("/preview");
  };

  const renderRow = (field: EditableField) => (
    <Row
      key={field.normKey}
      label={field.label}
      fieldKey={field.inputKey}
      value={field.value}
      unit={field.unit}
      optional={field.optional}
      invalid={(showErrors && blank.includes(field.label)) || Boolean(errors[field.normKey])}
      isUnread={unreadKeys.has(field.normKey) && field.value === null}
      isFlagged={flaggedKeys.has(field.normKey)}
      isCorrected={isCorrected(field.normKey)}
      error={errors[field.normKey]}
      onChange={(value, unit, err) => updateField(field.inputKey, value, unit, err)}
    />
  );

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      {/* Sheet photo header, so values can be checked against it */}
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
        <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-[#3e3e3e]/40 to-[#3e3e3e]" />
        <BackButton href="/preview" label="Back to the preview" className="absolute left-[31px] top-[48px]" />
        {photo && (
          <button
            type="button"
            onClick={() => setViewingPhoto(true)}
            aria-label="View the full sheet photo"
            className="absolute right-[30px] top-[48px] flex size-[28px] items-center justify-center rounded-full bg-[#117d69] text-white shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            <Icon name="eye" size={15} />
          </button>
        )}
      </div>

      <div className="relative -mt-[72px] px-[30px] pb-[48px] text-[#fcfcfc]">
        <h1 className="text-[24px] font-bold tracking-[0.02em]">Edit</h1>
        <p className="mt-[5px] text-[12px] leading-[1.5] text-[#fcfcfc]/90">
          {attentionFields.length > 0
            ? "Make sure the flagged numbers match your InBody report. Fix any that are wrong; anything you leave as it is counts as checked by you."
            : "Everything read cleanly. Change anything that doesn't match your sheet."}
        </p>

        {attentionFields.length > 0 ? (
          <>
            {unreadKeys.size > 0 && (
              <p className="mt-[14px] rounded-[8px] bg-rose-400/15 p-[10px] text-[11px] leading-relaxed text-rose-100">
                <span className="font-bold">Couldn&apos;t be read.</span> Blank boxes weren&apos;t
                readable at all. Type those straight off your sheet.
              </p>
            )}
            {flaggedKeys.size > 0 && (
              <p className="mt-[8px] rounded-[8px] bg-amber-400/15 p-[10px] text-[11px] leading-relaxed text-amber-100">
                <span className="font-bold">These don&apos;t add up.</span> Weight, body fat and
                lean mass should agree with each other, and here they don&apos;t, so one is
                probably misread. Your sheet is the only way to tell which.
              </p>
            )}

            <h2 className="mt-[24px] text-[16px] font-bold">Needs a check</h2>
            <div className="mt-[8px]">{attentionFields.map(renderRow)}</div>

            <div className="my-[18px] h-px bg-[#fcfcfc]/30" />

            <button
              type="button"
              onClick={() => setShowWholeSheet((v) => !v)}
              aria-expanded={showWholeSheet}
              className="flex w-full items-center justify-between text-[12px] font-bold text-[#7ee0cf]"
            >
              <span>
                {showWholeSheet ? "Hide" : "Show"} the other {otherFields.length} values
              </span>
              <span aria-hidden="true">{showWholeSheet ? "−" : "+"}</span>
            </button>
            {showWholeSheet && (
              <>
                <p className="mt-1 text-[10px] text-white/60">
                  These read cleanly. Edit any of them if the sheet says otherwise.
                </p>
                <div className="mt-2">{otherFields.map(renderRow)}</div>
              </>
            )}
          </>
        ) : (
          <div className="mt-[20px]">{allFields.map(renderRow)}</div>
        )}

        {/* Errors, gathered in one place above the single submit. */}
        {showErrors && blank.length > 0 && (
          <p role="alert" className="mt-4 text-[11px] font-medium text-rose-300">
            Fill in {blank.join(", ")} before continuing.
          </p>
        )}
        {showErrors && crossFieldError && (
          <p role="alert" className="mt-2 text-[11px] font-medium text-rose-300">
            {crossFieldError}
          </p>
        )}
        {outOfRangeFlagged.length > 0 && (
          <p role="alert" className="mt-2 text-[11px] font-medium text-amber-200">
            {outOfRangeFlagged.map(getFieldLabel).join(", ")}{" "}
            {outOfRangeFlagged.length === 1 ? "is" : "are"} outside the range a real measurement
            can fall in, so {outOfRangeFlagged.length === 1 ? "it has" : "they have"} to be
            corrected.
          </p>
        )}

        <button
          type="button"
          onClick={handleSave}
          aria-disabled={!canSubmit}
          className={`${canSubmit ? btn.primary : btn.secondary} mt-[40px]`}
        >
          <Icon name="save" size={16} />
          Save
        </button>
        {attentionFields.length > 0 && reviewedUnchanged.length > 0 && (
          <p className="mt-2 text-center text-[10px] leading-relaxed text-white/60">
            Saving records {reviewedUnchanged.map(getFieldLabel).join(", ")} as checked by you
            and left as measured.
          </p>
        )}
      </div>

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
    </PhoneFrame>
  );
}
