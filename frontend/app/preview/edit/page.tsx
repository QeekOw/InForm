"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { loadJSON, saveJSON } from "@/lib/session";
import { DEFAULT_READING, SESSION_KEYS, type InBodyReading } from "@/lib/inbody";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";

function NumberField({
  value,
  onChange,
  unit,
  integer = false,
}: {
  value: number;
  onChange: (v: number) => void;
  unit: string;
  integer?: boolean;
}) {
  return (
    <span className="flex items-center gap-1 rounded-md border-[1.5px] border-[#d9d9d9] px-2 py-0.5">
      <input
        type="number"
        step={integer ? "1" : "0.01"}
        value={value}
        onChange={(e) => onChange(integer ? Math.round(Number(e.target.value)) : Number(e.target.value))}
        className="w-12 text-right text-[12px] font-bold outline-none"
      />
      <span className="text-[8px] font-medium">{unit}</span>
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
  value: number;
  unit: string;
  onChange: (v: number) => void;
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
  const [reading, setReading] = useState<InBodyReading>(DEFAULT_READING);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReading(loadJSON<InBodyReading>(SESSION_KEYS.reading) ?? DEFAULT_READING);
  }, []);

  const set = <K extends keyof InBodyReading>(key: K, value: number) =>
    setReading((r) => ({ ...r, [key]: value }));
  const setSeg = (key: keyof InBodyReading["segmental_lean"], value: number) =>
    setReading((r) => ({ ...r, segmental_lean: { ...r.segmental_lean, [key]: value } }));

  const handleConfirm = () => {
    saveJSON(SESSION_KEYS.reading, reading);
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
          <Row
            label="Weight"
            value={reading.weight_kg}
            unit="kg"
            onChange={(v) => set("weight_kg", v)}
          />
          <Row
            label="Lean Body Mass"
            value={reading.lean_body_mass_kg}
            unit="kg"
            onChange={(v) => set("lean_body_mass_kg", v)}
          />
          <Row
            label="Percent Body Fat"
            value={reading.percent_body_fat}
            unit="%"
            onChange={(v) => set("percent_body_fat", v)}
          />
          <Row
            label="Skeletal Muscle Mass"
            value={reading.skeletal_muscle_mass_kg}
            unit="kg"
            onChange={(v) => set("skeletal_muscle_mass_kg", v)}
          />
          <Row
            label="Visceral Fat Level"
            value={reading.visceral_fat_level}
            unit=""
            integer
            onChange={(v) => set("visceral_fat_level", v)}
          />
        </div>

        <div className="my-4 h-px bg-black/10" />

        <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
        <div className="mt-3 grid grid-cols-2 gap-x-4">
          <div>
            <Row
              label="Left Arm"
              value={reading.segmental_lean.left_arm_kg}
              unit="kg"
              onChange={(v) => setSeg("left_arm_kg", v)}
            />
            <Row
              label="Right Arm"
              value={reading.segmental_lean.right_arm_kg}
              unit="kg"
              onChange={(v) => setSeg("right_arm_kg", v)}
            />
            <Row
              label="Trunk"
              value={reading.segmental_lean.trunk_kg}
              unit="kg"
              onChange={(v) => setSeg("trunk_kg", v)}
            />
          </div>
          <div>
            <Row
              label="Left Leg"
              value={reading.segmental_lean.left_leg_kg}
              unit="kg"
              onChange={(v) => setSeg("left_leg_kg", v)}
            />
            <Row
              label="Right Leg"
              value={reading.segmental_lean.right_leg_kg}
              unit="kg"
              onChange={(v) => setSeg("right_leg_kg", v)}
            />
          </div>
        </div>

        <div className="my-4 h-px bg-black/10" />

        <Row
          label="Basal Metabolic Rate"
          value={reading.basal_metabolic_rate_kcal}
          unit="kcal"
          onChange={(v) => set("basal_metabolic_rate_kcal", v)}
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
