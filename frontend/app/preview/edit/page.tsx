"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { loadJSON, removeSessionItem, saveJSON } from "@/lib/session";
import {
  BODY_COMPOSITION_FIELDS,
  DEFAULT_READING,
  SEGMENTAL_LEAN_LEFT_FIELDS,
  SEGMENTAL_LEAN_RIGHT_FIELDS,
  SESSION_KEYS,
  type InBodyPayload,
  type ScalarInBodyField,
} from "@/lib/inbody";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";

function NumberField({
  value,
  onChange,
  unit,
  integer = false,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
  unit: string;
  integer?: boolean;
}) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.trim();
    if (raw === "") {
      onChange(null);
      return;
    }
    const num = Number(raw);
    if (Number.isNaN(num)) return;
    onChange(integer ? Math.round(num) : num);
  };

  return (
    <span className="flex items-center gap-1 rounded-md border-[1.5px] border-[#d9d9d9] px-2 py-0.5">
      <input
        type="number"
        step={integer ? "1" : "0.01"}
        value={value ?? ""}
        placeholder={value == null ? "None" : undefined}
        onChange={handleChange}
        className="w-12 text-right text-[12px] font-bold outline-none"
      />
      {unit ? <span className="text-[8px] font-medium">{unit}</span> : null}
    </span>
  );
}

function Row({
  label,
  value,
  unit,
  onChange,
  integer = false,
}: {
  label: string;
  value: number | null;
  unit: string;
  onChange: (v: number | null) => void;
  integer?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1 text-[12px]">
      <span>{label}</span>
      <NumberField value={value} onChange={onChange} unit={unit} integer={integer} />
    </div>
  );
}

export default function PreviewEdit() {
  const router = useRouter();
  const [reading, setReading] = useState<InBodyPayload>(DEFAULT_READING);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReading(loadJSON<InBodyPayload>(SESSION_KEYS.reading) ?? DEFAULT_READING);
  }, []);

  const updateField = (key: ScalarInBodyField, value: number | null) => {
    setReading((prev) => ({ ...prev, [key]: value }));
  };

  const updateSegmentalLean = (
    key: keyof InBodyPayload["segmental_lean"],
    value: number | null,
  ) => {
    setReading((prev) => ({
      ...prev,
      segmental_lean: {
        ...prev.segmental_lean,
        [key]: value ?? 0,
      },
    }));
  };

  const handleConfirm = () => {
    saveJSON(SESSION_KEYS.reading, reading);
    // ADR-0011 §3: Zero Image Persistence for User Uploads - clear on confirm
    removeSessionItem(SESSION_KEYS.photo);
    router.push("/result");
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
              value={reading[field.key]}
              unit={field.unit}
              integer={field.integer}
              onChange={(val) => updateField(field.key, val)}
            />
          ))}
        </div>

        <div className="my-4 h-px bg-black/10" />

        <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
        <div className="mt-3 grid grid-cols-2 gap-x-4">
          <div>
            {SEGMENTAL_LEAN_LEFT_FIELDS.map((field) => (
              <Row
                key={field.key}
                label={field.label}
                value={reading.segmental_lean[field.key]}
                unit={field.unit}
                onChange={(val) => updateSegmentalLean(field.key, val)}
              />
            ))}
          </div>
          <div>
            {SEGMENTAL_LEAN_RIGHT_FIELDS.map((field) => (
              <Row
                key={field.key}
                label={field.label}
                value={reading.segmental_lean[field.key]}
                unit={field.unit}
                onChange={(val) => updateSegmentalLean(field.key, val)}
              />
            ))}
          </div>
        </div>

        <div className="my-4 h-px bg-black/10" />

        <Row
          label="Basal Metabolic Rate"
          value={reading.basal_metabolic_rate_kcal}
          unit="kcal"
          onChange={(val) => updateField("basal_metabolic_rate_kcal", val)}
        />

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
