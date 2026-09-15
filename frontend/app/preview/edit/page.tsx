"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import {
  FIELD_CONSTRAINTS,
  normalizeFieldKey,
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
import { loadJSON, SESSION_KEYS } from "@/lib/session";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";

function NumberField({
  value,
  onChange,
  unit,
  integer = false,
  invalid = false,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
  unit: string;
  integer?: boolean;
  invalid?: boolean;
}) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.trim();
    if (raw === "") {
      onChange(null);
      return;
    }
    const num = Number(raw);
    if (!Number.isNaN(num)) onChange(integer ? Math.round(num) : num);
  };

  return (
    <span
      className={`flex items-center gap-1 rounded-md border-[1.5px] px-2 py-0.5 ${
        invalid ? "border-red-500 bg-red-50/50" : "border-[#d9d9d9]"
      }`}
    >
      <input
        type="number"
        step={integer ? "1" : "0.01"}
        value={value ?? ""}
        placeholder="—"
        aria-invalid={invalid}
        onChange={handleChange}
        className="w-16 text-right text-[12px] font-bold outline-none bg-transparent"
      />
      {unit && <span className="text-[8px] font-medium opacity-60">{unit}</span>}
    </span>
  );
}

function Row({
  label,
  value,
  unit,
  onChange,
  integer = false,
  invalid = false,
  isUnread = false,
  error = null,
}: {
  label: string;
  value: number | null;
  unit: string;
  onChange: (v: number | null) => void;
  integer?: boolean;
  invalid?: boolean;
  isUnread?: boolean;
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
        </span>
        <NumberField
          value={value}
          onChange={onChange}
          unit={unit}
          integer={integer}
          invalid={invalid}
        />
      </div>
      {error && <p className="mt-0.5 text-right text-[10px] text-red-600 font-medium">{error}</p>}
    </div>
  );
}

export default function PreviewEdit() {
  const router = useRouter();
  const [draft, setDraft] = useState<InBodyDraft>(DEFAULT_READING);
  const [corrections, setCorrections] = useState<Record<string, { value: number; unit?: string }>>({});
  const [unreadKeys, setUnreadKeys] = useState<Set<string>>(new Set());
  const [showErrors, setShowErrors] = useState(false);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    const storedReading = loadJSON<InBodyPayload>(SESSION_KEYS.reading);
    const storedCorrections =
      loadJSON<Record<string, { value: number; unit?: string }>>(SESSION_KEYS.corrections) ?? {};
    const extraction = loadJSON<SampleExtraction>(SESSION_KEYS.extraction);

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDraft(storedReading ?? DEFAULT_READING);
    setCorrections(storedCorrections);
    if (extraction?.unread) {
      setUnreadKeys(new Set(extraction.unread.map(normalizeFieldKey)));
    }
  }, []);

  const setField = (key: ScalarInBodyField, value: number | null) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    const normKey = normalizeFieldKey(key);
    const unit = FIELD_CONSTRAINTS[normKey]?.unit;
    if (value !== null) {
      setCorrections((prev) => ({ ...prev, [normKey]: { value, unit } }));
    } else {
      setCorrections((prev) => {
        const next = { ...prev };
        delete next[normKey];
        return next;
      });
    }
  };

  const setSegment = (key: SegmentalLeanField, value: number | null) => {
    setDraft((prev) => ({
      ...prev,
      segmental_lean: { ...prev.segmental_lean, [key]: value },
    }));
    const normKey = normalizeFieldKey(key);
    const unit = FIELD_CONSTRAINTS[normKey]?.unit;
    if (value !== null) {
      setCorrections((prev) => ({ ...prev, [normKey]: { value, unit } }));
    } else {
      setCorrections((prev) => {
        const next = { ...prev };
        delete next[normKey];
        return next;
      });
    }
  };

  // Field validation checks (AC: An out-of-range or wrong-unit value is rejected before the plan is computed)
  const getFieldError = (key: string, value: number | null): string | null => {
    if (value === null) return null;
    return validateFieldValue(key, value);
  };

  const weightError = getFieldError("weight_kg", draft.weight_kg);
  const lbmError = getFieldError("lean_body_mass_kg", draft.lean_body_mass_kg);
  const pbfError = getFieldError("percent_body_fat", draft.percent_body_fat);
  const smmError = getFieldError("skeletal_muscle_mass_kg", draft.skeletal_muscle_mass_kg);
  const bmrError = getFieldError("basal_metabolic_rate_kcal", draft.basal_metabolic_rate_kcal);
  const visceralError = getFieldError("visceral_fat_level", draft.visceral_fat_level);

  const segmentErrors: Record<SegmentalLeanField, string | null> = {
    left_arm_kg: getFieldError("left_arm_kg", draft.segmental_lean.left_arm_kg),
    right_arm_kg: getFieldError("right_arm_kg", draft.segmental_lean.right_arm_kg),
    left_leg_kg: getFieldError("left_leg_kg", draft.segmental_lean.left_leg_kg),
    right_leg_kg: getFieldError("right_leg_kg", draft.segmental_lean.right_leg_kg),
    trunk_kg: getFieldError("trunk_kg", draft.segmental_lean.trunk_kg),
  };

  // Cross-field physiological checks
  let crossFieldError: string | null = null;
  if (draft.weight_kg != null && draft.lean_body_mass_kg != null && draft.lean_body_mass_kg > draft.weight_kg) {
    crossFieldError = "Lean Body Mass cannot exceed total Weight.";
  } else if (
    draft.lean_body_mass_kg != null &&
    draft.skeletal_muscle_mass_kg != null &&
    draft.skeletal_muscle_mass_kg > draft.lean_body_mass_kg
  ) {
    crossFieldError = "Skeletal Muscle Mass cannot exceed Lean Body Mass.";
  }

  const blank = blankRequiredFields(draft);
  const hasRangeErrors = Boolean(
    weightError ||
      lbmError ||
      pbfError ||
      smmError ||
      bmrError ||
      visceralError ||
      Object.values(segmentErrors).some(Boolean) ||
      crossFieldError,
  );

  const handleConfirm = () => {
    if (blank.length > 0 || hasRangeErrors) {
      setShowErrors(true);
      return;
    }

    // Every required field is filled and valid.
    // Store corrections alongside measured fields (never merged into them)
    router.push(confirmReading(draft as InBodyPayload, corrections));
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

          <h2 className="text-[14px] font-bold">Body Composition</h2>
          <div className="mt-3">
            {BODY_COMPOSITION_FIELDS.map((field) => {
              const normKey = normalizeFieldKey(field.key);
              const error =
                field.key === "weight_kg"
                  ? weightError
                  : field.key === "lean_body_mass_kg"
                  ? lbmError
                  : field.key === "percent_body_fat"
                  ? pbfError
                  : field.key === "skeletal_muscle_mass_kg"
                  ? smmError
                  : field.key === "visceral_fat_level"
                  ? visceralError
                  : null;

              return (
                <Row
                  key={field.key}
                  label={field.label}
                  value={draft[field.key]}
                  unit={field.key === "visceral_fat_level" ? "level" : field.unit}
                  integer={field.integer}
                  invalid={(showErrors && blank.includes(field.label)) || Boolean(error)}
                  isUnread={unreadKeys.has(normKey) && draft[field.key] === null}
                  error={showErrors ? error : null}
                  onChange={(value) => setField(field.key, value)}
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
                  const error = segmentErrors[field.key];

                  return (
                    <Row
                      key={field.key}
                      label={field.label}
                      value={draft.segmental_lean[field.key]}
                      unit={field.unit}
                      invalid={(showErrors && blank.includes(field.label)) || Boolean(error)}
                      isUnread={unreadKeys.has(normKey) && draft.segmental_lean[field.key] === null}
                      error={showErrors ? error : null}
                      onChange={(value) => setSegment(field.key, value)}
                    />
                  );
                })}
              </div>
            ))}
          </div>

          <div className="my-4 h-px bg-black/10" />

          <Row
            label={BMR_FIELD.label}
            value={draft[BMR_FIELD.key]}
            unit={BMR_FIELD.unit}
            invalid={(showErrors && blank.includes(BMR_FIELD.label)) || Boolean(bmrError)}
            isUnread={unreadKeys.has(BMR_FIELD.key) && draft[BMR_FIELD.key] === null}
            error={showErrors ? bmrError : null}
            onChange={(value) => setField(BMR_FIELD.key, value)}
          />

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
