"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { confirmReading } from "@/lib/flow";
import { loadJSON, SESSION_KEYS } from "@/lib/session";
import {
  BMR_FIELD,
  BODY_COMPOSITION_FIELDS,
  DEFAULT_READING,
  SEGMENTAL_LEAN_COLUMNS,
  blankRequiredFields,
  type InBodyDraft,
  type InBodyPayload,
  type ScalarInBodyField,
  type SegmentalLeanField,
} from "@/lib/inbody";

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
        invalid ? "border-red-500" : "border-[#d9d9d9]"
      }`}
    >
      <input
        type="number"
        step={integer ? "1" : "0.01"}
        value={value ?? ""}
        placeholder="—"
        aria-invalid={invalid}
        onChange={handleChange}
        className="w-12 text-right text-[12px] font-bold outline-none"
      />
      {unit && <span className="text-[8px] font-medium">{unit}</span>}
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
}: {
  label: string;
  value: number | null;
  unit: string;
  onChange: (v: number | null) => void;
  integer?: boolean;
  invalid?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1 text-[12px]">
      <span>{label}</span>
      <NumberField
        value={value}
        onChange={onChange}
        unit={unit}
        integer={integer}
        invalid={invalid}
      />
    </div>
  );
}

export default function PreviewEdit() {
  const router = useRouter();
  const [draft, setDraft] = useState<InBodyDraft>(DEFAULT_READING);
  const [showErrors, setShowErrors] = useState(false);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDraft(loadJSON<InBodyPayload>(SESSION_KEYS.reading) ?? DEFAULT_READING);
  }, []);

  const setField = (key: ScalarInBodyField, value: number | null) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const setSegment = (key: SegmentalLeanField, value: number | null) => {
    setDraft((prev) => ({
      ...prev,
      segmental_lean: { ...prev.segmental_lean, [key]: value },
    }));
  };

  const blank = showErrors ? blankRequiredFields(draft) : [];

  const handleConfirm = () => {
    if (blankRequiredFields(draft).length > 0) {
      setShowErrors(true);
      return;
    }
    // Every required field is filled, so the draft is a complete payload.
    router.push(confirmReading(draft as InBodyPayload));
  };

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="flex items-center gap-3 px-[30px] pt-[62px]">
        <button
          type="button"
          onClick={() => router.back()}
          className="flex size-8 items-center justify-center rounded-full bg-white shadow-md"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="Back" className="size-[18px]" src={imgBack} />
        </button>
        <h1 className="text-[24px] font-bold text-[#fcfcfc]">Preview</h1>
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
        <h2 className="text-[14px] font-bold">Body Composition</h2>
        <div className="mt-3">
          {BODY_COMPOSITION_FIELDS.map((field) => (
            <Row
              key={field.key}
              label={field.label}
              value={draft[field.key]}
              unit={field.unit}
              integer={field.integer}
              invalid={blank.includes(field.label)}
              onChange={(value) => setField(field.key, value)}
            />
          ))}
        </div>

        <div className="my-4 h-px bg-black/10" />

        <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
        <div className="mt-3 grid grid-cols-2 gap-x-4">
          {SEGMENTAL_LEAN_COLUMNS.map((column) => (
            <div key={column[0].key}>
              {column.map((field) => (
                <Row
                  key={field.key}
                  label={field.label}
                  value={draft.segmental_lean[field.key]}
                  unit={field.unit}
                  invalid={blank.includes(field.label)}
                  onChange={(value) => setSegment(field.key, value)}
                />
              ))}
            </div>
          ))}
        </div>

        <div className="my-4 h-px bg-black/10" />

        <Row
          label={BMR_FIELD.label}
          value={draft[BMR_FIELD.key]}
          unit={BMR_FIELD.unit}
          invalid={blank.includes(BMR_FIELD.label)}
          onChange={(value) => setField(BMR_FIELD.key, value)}
        />

        {blank.length > 0 && (
          <p role="alert" className="mt-4 text-[11px] text-red-600">
            Fill in {blank.join(", ")} before confirming.
          </p>
        )}

        <button
          type="button"
          onClick={handleConfirm}
          className="mt-6 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white"
        >
          Confirm
        </button>
      </div>
    </PhoneFrame>
  );
}
