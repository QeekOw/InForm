"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import {
  FIELD_CONSTRAINTS,
  getFieldLabel,
  normalizeFieldKey,
  parseAndValidateFieldInput,
  validateFieldValue,
} from "@/lib/corrections";
import { confirmReading } from "@/lib/flow";
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
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";

function isSegmentField(key: string): key is SegmentalLeanField {
  return (
    key === "left_arm_kg" ||
    key === "right_arm_kg" ||
    key === "left_leg_kg" ||
    key === "right_leg_kg" ||
    key === "trunk_kg"
  );
}

function ValueField({
  value,
  fieldKey,
  unit,
  invalid = false,
  onFieldChange,
}: {
  value: number | null;
  fieldKey: string;
  unit: string;
  invalid?: boolean;
  onFieldChange: (val: number | null, unit?: string, error?: string | null) => void;
}) {
  const [typedText, setTypedText] = useState<string | null>(null);

  const displayValue = typedText !== null ? typedText : (value != null ? String(value) : "");

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
      className={`flex items-center gap-1 rounded-md border-[1.5px] px-2 py-0.5 ${
        invalid ? "border-red-500 bg-red-50/50" : "border-[#d9d9d9]"
      }`}
    >
      <input
        type="text"
        value={displayValue}
        placeholder="—"
        aria-invalid={invalid}
        onBlur={handleBlur}
        onChange={handleChange}
        className="w-20 text-right text-[12px] font-bold outline-none bg-transparent"
      />
      {unit && <span className="text-[8px] font-medium opacity-60">{unit}</span>}
    </span>
  );
}

function Row({
  label,
  fieldKey,
  value,
  unit,
  onChange,
  invalid = false,
  isUnread = false,
  isFlagged = false,
  isConfirmed = false,
  onConfirm,
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
  isConfirmed?: boolean;
  onConfirm?: () => void;
  error?: string | null;
}) {
  return (
    <div className="py-1">
      <div className="flex items-center justify-between text-[12px]">
        <span className="flex items-center gap-1.5">
          <span>{label}</span>
          {isUnread && (
            <span className="rounded bg-rose-200 px-1 py-0.5 text-[8px] font-bold text-rose-800">
              Unread
            </span>
          )}
          {isFlagged && !isConfirmed && (
            <span className="inline-flex items-center gap-1">
              <span className="rounded bg-amber-200 px-1 py-0.5 text-[8px] font-bold text-amber-800">
                Flagged Check
              </span>
              {onConfirm && (
                <button
                  type="button"
                  onClick={onConfirm}
                  className="rounded bg-[#117d69] px-1.5 py-0.5 text-[8px] font-bold text-white shadow-xs hover:bg-[#0e6353]"
                >
                  Confirm
                </button>
              )}
            </span>
          )}
          {isConfirmed && (
            <span className="inline-flex items-center gap-1">
              <span className="rounded bg-emerald-200 px-1 py-0.5 text-[8px] font-bold text-emerald-800">
                ✓ Confirmed
              </span>
              {onConfirm && (
                <button
                  type="button"
                  onClick={onConfirm}
                  className="text-[8px] font-medium text-zinc-500 hover:text-zinc-700 underline"
                  title="Undo confirmation"
                >
                  Undo
                </button>
              )}
            </span>
          )}
        </span>
        <ValueField
          value={value}
          fieldKey={fieldKey}
          unit={unit}
          invalid={invalid}
          onFieldChange={onChange}
        />
      </div>
      {error && <p role="alert" className="mt-0.5 text-right text-[10px] font-medium text-red-600">{error}</p>}
    </div>
  );
}

export default function PreviewEdit() {
  const router = useRouter();
  const [draft, setDraft] = useState<InBodyDraft>(DEFAULT_READING);
  const [corrections, setCorrections] = useState<Record<string, { value: number; unit?: string }>>({});
  const [confirmedKeys, setConfirmedKeys] = useState<Set<string>>(new Set());
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

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExtraction(loadedExtraction);
    setCorrections(storedCorrections);

    const storedConfirmations = loadJSON<string[]>(SESSION_KEYS.confirmations) ?? [];
    setConfirmedKeys(new Set(storedConfirmations.map(normalizeFieldKey)));
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

    // If there are unread fields, ensure they are NOT prefilled with demo/default values
    // unless a user correction was already stored for that field.
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

    // Apply any previously stored corrections to the base draft
    for (const [rawKey, corr] of Object.entries(storedCorrections)) {
      const normKey = normalizeFieldKey(rawKey);
      const val =
        typeof corr === "object" && corr !== null && "value" in corr
          ? corr.value
          : Number(corr);
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
      setCorrections((prev) => ({
        ...prev,
        [normKey]: { value, ...(resolvedUnit ? { unit: resolvedUnit } : {}) },
      }));
      // AC: Correcting a flagged value records a corrected field, not confirmed.
      setConfirmedKeys((prev) => {
        const next = new Set(prev);
        if (next.has(normKey)) {
          next.delete(normKey);
          saveJSON(SESSION_KEYS.confirmations, Array.from(next));
        }
        return next;
      });
    } else {
      setCorrections((prev) => {
        const next = { ...prev };
        delete next[normKey];
        delete next[key];
        return next;
      });
    }
  };

  const handleToggleConfirm = (fieldKey: string) => {
    const norm = normalizeFieldKey(fieldKey);
    setConfirmedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(norm)) {
        next.delete(norm);
      } else {
        next.add(norm);
        // If confirmed, remove from corrections so it stays a measured field!
        setCorrections((c) => {
          const nextC = { ...c };
          delete nextC[norm];
          delete nextC[fieldKey];
          return nextC;
        });
      }
      saveJSON(SESSION_KEYS.confirmations, Array.from(next));
      return next;
    });
  };

  const getFieldError = (normKey: string, value: number | null): string | null => {
    if (fieldErrors[normKey] !== undefined) {
      return fieldErrors[normKey];
    }
    return validateFieldValue(normKey, value);
  };

  const errors: Record<string, string | null> = {
    weight_kg: getFieldError("weight_kg", draft.weight_kg),
    lean_body_mass_kg: getFieldError("lean_body_mass_kg", draft.lean_body_mass_kg),
    percent_body_fat: getFieldError("percent_body_fat", draft.percent_body_fat),
    skeletal_muscle_mass_kg: getFieldError("skeletal_muscle_mass_kg", draft.skeletal_muscle_mass_kg),
    visceral_fat_level: getFieldError("visceral_fat_level", draft.visceral_fat_level),
    basal_metabolic_rate_kcal: getFieldError("basal_metabolic_rate_kcal", draft.basal_metabolic_rate_kcal),
    "segmental_lean.left_arm_kg": getFieldError(
      "segmental_lean.left_arm_kg",
      draft.segmental_lean?.left_arm_kg ?? null,
    ),
    "segmental_lean.right_arm_kg": getFieldError(
      "segmental_lean.right_arm_kg",
      draft.segmental_lean?.right_arm_kg ?? null,
    ),
    "segmental_lean.left_leg_kg": getFieldError(
      "segmental_lean.left_leg_kg",
      draft.segmental_lean?.left_leg_kg ?? null,
    ),
    "segmental_lean.right_leg_kg": getFieldError(
      "segmental_lean.right_leg_kg",
      draft.segmental_lean?.right_leg_kg ?? null,
    ),
    "segmental_lean.trunk_kg": getFieldError(
      "segmental_lean.trunk_kg",
      draft.segmental_lean?.trunk_kg ?? null,
    ),
  };

  let crossFieldError: string | null = null;
  if (
    draft.weight_kg != null &&
    draft.lean_body_mass_kg != null &&
    draft.lean_body_mass_kg > draft.weight_kg
  ) {
    crossFieldError = "Lean Body Mass cannot exceed total Weight.";
  }

  const blank = blankRequiredFields(draft);
  const hasRangeErrors = Boolean(
    Object.values(errors).some(Boolean) || crossFieldError,
  );

  const unresolvedFlagged = Array.from(flaggedKeys).filter(
    (f) => !(f in corrections) && !confirmedKeys.has(f),
  );

  const handleConfirm = () => {
    if (blank.length > 0 || hasRangeErrors || unresolvedFlagged.length > 0) {
      setShowErrors(true);
      return;
    }

    // Every required field is filled and valid.
    // Store corrections alongside measured fields (never merged into them)
    router.push(
      confirmReading(
        draft as InBodyPayload,
        corrections,
        extraction?.data,
        Array.from(confirmedKeys),
      ),
    );
  };

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="max-h-screen overflow-y-auto pb-10">
        <div className="flex items-center gap-3 px-[30px] pt-[62px]">
          <button
            type="button"
            onClick={() => router.back()}
            className="flex size-8 items-center justify-center rounded-full bg-white shadow-md"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="Back" className="size-[18px]" src={imgBack} />
          </button>
          <h1 className="text-[24px] font-bold text-[#fcfcfc]">Edit Values</h1>
        </div>

        <div className="relative mx-[30px] mt-[31px] h-[201px] overflow-hidden rounded-[15px] bg-[#1f1f1f]">
          <ReportPhoto />
          <Link
            href="/upload/capture"
            className="absolute right-4 top-4 flex h-8 items-center gap-[10px] rounded-lg bg-[#117d69] px-[10px] text-[12px] font-bold text-white"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-[14px]" src={imgCamera} />
            Retake
          </Link>
        </div>

        <div className="mx-[30px] mt-[18px] rounded-[15px] bg-white p-[25px] text-black">
          {unreadKeys.size > 0 && (
            <div className="mb-4 rounded-lg border border-rose-300 bg-rose-50 p-2.5 text-[11px] text-rose-900">
              <span className="font-bold">Enter unread values:</span> Type the missing values off your sheet. They are recorded as your corrections.
            </div>
          )}
          {unresolvedFlagged.length > 0 && (
            <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-2.5 text-[11px] text-amber-900">
              <span className="font-bold">Verify flagged values:</span>{" "}
              <span className="font-semibold">
                {unresolvedFlagged.map(getFieldLabel).join(", ")}
              </span>{" "}
              triggered physiological cross-checks. Confirm unchanged values or edit them.
            </div>
          )}

          <h2 className="text-[14px] font-bold">Body Composition</h2>
          <div className="mt-3">
            {BODY_COMPOSITION_FIELDS.map((field) => {
              const normKey = normalizeFieldKey(field.key);
              const error = errors[normKey];
              const isFlagged = flaggedKeys.has(normKey) && !(normKey in corrections);
              const isConfirmed = confirmedKeys.has(normKey) && !(normKey in corrections);

              return (
                <Row
                  key={field.key}
                  label={field.label}
                  fieldKey={field.key}
                  value={draft[field.key]}
                  unit={field.key === "visceral_fat_level" ? "level" : field.unit}
                  invalid={(showErrors && blank.includes(field.label)) || Boolean(error)}
                  isUnread={unreadKeys.has(normKey) && draft[field.key] === null}
                  isFlagged={isFlagged}
                  isConfirmed={isConfirmed}
                  onConfirm={() => handleToggleConfirm(field.key)}
                  error={error}
                  onChange={(value, unit, err) => updateField(field.key, value, unit, err)}
                />
              );
            })}
          </div>

          <div className="my-4 h-px bg-black/10" />

          <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
          <div className="mt-3 grid grid-cols-2 gap-x-4">
            {SEGMENTAL_LEAN_COLUMNS.map((column) => (
              <div key={column[0].key}>
                {column.map((field) => {
                  const normKey = normalizeFieldKey(field.key);
                  const dottedKey = `segmental_lean.${field.key}`;
                  const error = errors[normKey];
                  const isFlagged =
                    (flaggedKeys.has(dottedKey) || flaggedKeys.has(normKey)) &&
                    !(normKey in corrections) &&
                    !(dottedKey in corrections);
                  const isConfirmed =
                    (confirmedKeys.has(dottedKey) || confirmedKeys.has(normKey)) &&
                    !(normKey in corrections) &&
                    !(dottedKey in corrections);

                  return (
                    <Row
                      key={field.key}
                      label={field.label}
                      fieldKey={field.key}
                      value={draft.segmental_lean[field.key]}
                      unit={field.unit}
                      invalid={(showErrors && blank.includes(field.label)) || Boolean(error)}
                      isUnread={unreadKeys.has(normKey) && draft.segmental_lean[field.key] === null}
                      isFlagged={isFlagged}
                      isConfirmed={isConfirmed}
                      onConfirm={() => handleToggleConfirm(dottedKey)}
                      error={error}
                      onChange={(value, unit, err) => updateField(field.key, value, unit, err)}
                    />
                  );
                })}
              </div>
            ))}
          </div>

          <div className="my-4 h-px bg-black/10" />

          {(() => {
            const normBmrKey = normalizeFieldKey(BMR_FIELD.key);
            const bmrError = errors[normBmrKey];
            const isFlagged = flaggedKeys.has(normBmrKey) && !(normBmrKey in corrections);
            const isConfirmed = confirmedKeys.has(normBmrKey) && !(normBmrKey in corrections);
            return (
              <Row
                label={BMR_FIELD.label}
                fieldKey={BMR_FIELD.key}
                value={draft[BMR_FIELD.key]}
                unit={BMR_FIELD.unit}
                invalid={(showErrors && blank.includes(BMR_FIELD.label)) || Boolean(bmrError)}
                isUnread={unreadKeys.has(normBmrKey) && draft[BMR_FIELD.key] === null}
                isFlagged={isFlagged}
                isConfirmed={isConfirmed}
                onConfirm={() => handleToggleConfirm(BMR_FIELD.key)}
                error={bmrError}
                onChange={(value, unit, err) => updateField(BMR_FIELD.key, value, unit, err)}
              />
            );
          })()}

          {showErrors && blank.length > 0 && (
            <p role="alert" className="mt-4 text-[11px] text-red-600 font-medium">
              Fill in {blank.join(", ")} before confirming.
            </p>
          )}

          {showErrors && crossFieldError && (
            <p role="alert" className="mt-2 text-[11px] text-red-600 font-medium">
              {crossFieldError}
            </p>
          )}

          {showErrors && unresolvedFlagged.length > 0 && (
            <p role="alert" className="mt-2 text-[11px] text-amber-700 font-medium">
              Building a plan is impossible while a flagged field is unresolved. Please confirm or correct: {unresolvedFlagged.map(getFieldLabel).join(", ")}.
            </p>
          )}

          <button
            type="button"
            onClick={handleConfirm}
            className="mt-6 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white shadow-sm"
          >
            Confirm
          </button>
        </div>
      </div>
    </PhoneFrame>
  );
}
