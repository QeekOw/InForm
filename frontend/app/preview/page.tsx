"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import { loadJSON, saveJSON } from "@/lib/session";
import { DEFAULT_READING, SESSION_KEYS, type InBodyReading } from "@/lib/inbody";

const imgBack = "/icons/preview/back-arrow.svg";
const imgCamera = "/icons/preview/camera-icon.svg";
const imgEdit = "/icons/preview/edit-icon.svg";

function Row({ label, value, unit }: { label: string; value: string | number; unit: string }) {
  return (
    <div className="flex items-baseline justify-between py-1 text-[12px]">
      <span>{label}</span>
      <span className="font-bold">
        {value} <span className="text-[8px] font-medium">{unit}</span>
      </span>
    </div>
  );
}

export default function Preview() {
  const router = useRouter();
  const [reading, setReading] = useState<InBodyReading>(DEFAULT_READING);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR —
    // this is exactly the "synchronize with an external system" case, not
    // state derived from props/state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReading(loadJSON<InBodyReading>(SESSION_KEYS.reading) ?? DEFAULT_READING);
  }, []);

  const handleConfirm = () => {
    saveJSON(SESSION_KEYS.reading, reading);
    router.push("/result");
  };

  const { segmental_lean: seg } = reading;

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

      <div className="relative mx-[30px] mt-[31px] h-[201px] overflow-hidden rounded-[15px] bg-[#1f1f1f]">
        <p className="absolute inset-0 flex items-center justify-center text-[12px] text-white/40">
          Your report photo
        </p>
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
          <Row label="Weight" value={reading.weight_kg} unit="kg" />
          <Row label="Lean Body Mass" value={reading.lean_body_mass_kg} unit="kg" />
          <Row label="Percent Body Fat" value={reading.percent_body_fat} unit="%" />
          <Row label="Skeletal Muscle Mass" value={reading.skeletal_muscle_mass_kg} unit="kg" />
          <Row label="Visceral Fat Level" value={`Level ${reading.visceral_fat_level}`} unit="" />
        </div>

        <div className="my-4 h-px bg-black/10" />

        <h2 className="text-[14px] font-bold">Segmental Lean Analysis</h2>
        <div className="mt-3 grid grid-cols-2 gap-x-6">
          <div>
            <Row label="Left Arm" value={seg.left_arm_kg} unit="kg" />
            <Row label="Right Arm" value={seg.right_arm_kg} unit="kg" />
            <Row label="Trunk" value={seg.trunk_kg} unit="kg" />
          </div>
          <div>
            <Row label="Left Leg" value={seg.left_leg_kg} unit="kg" />
            <Row label="Right Leg" value={seg.right_leg_kg} unit="kg" />
          </div>
        </div>

        <div className="my-4 h-px bg-black/10" />

        <Row label="Basal Metabolic Rate" value={reading.basal_metabolic_rate_kcal} unit="kcal" />

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
          onClick={handleConfirm}
          className="mt-2 flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold text-white"
        >
          Confirm
        </button>
      </div>
    </PhoneFrame>
  );
}
