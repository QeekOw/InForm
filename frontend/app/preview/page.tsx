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
  type InBodyPayload,
} from "@/lib/inbody";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";
const imgEdit = "/icons/preview/edit-icon.svg";

function Row({
  label,
  value,
  unit,
}: {
  label: string;
  value: string | number | null;
  unit: string;
}) {
  return (
    <div className="flex items-baseline justify-between py-1 text-[12px]">
      <span>{label}</span>
      <span className="font-bold">
        {value ?? "—"}{" "}
        {value != null && unit && <span className="text-[8px] font-medium">{unit}</span>}
      </span>
    </div>
  );
}

export default function Preview() {
  const router = useRouter();
  const [reading, setReading] = useState<InBodyPayload>(DEFAULT_READING);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR —
    // this is exactly the "synchronize with an external system" case, not
    // state derived from props/state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReading(loadJSON<InBodyPayload>(SESSION_KEYS.reading) ?? DEFAULT_READING);
  }, []);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
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

      <div className="relative mx-[30px] mt-[24px] h-[201px] overflow-hidden rounded-[15px] bg-[#1f1f1f]">
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

      <div className="mx-[30px] mt-3 flex items-center justify-between rounded-lg bg-white/10 px-3 py-1.5 text-[11px] text-white/90">
        <span className="font-medium">Demo baseline values</span>
        <span className="text-[10px] text-white/60">Pending OCR extraction · edit below</span>
      </div>

      <div className="mx-[30px] mt-[14px] rounded-[15px] bg-white p-[25px] text-black">
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
          onClick={() => router.push(confirmReading(reading))}
          className="mt-2 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white"
        >
          Confirm
        </button>
      </div>
    </PhoneFrame>
  );
}
