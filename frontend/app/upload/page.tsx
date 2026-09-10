"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PhoneFrame from "@/components/PhoneFrame";
import { saveJSON } from "@/lib/session";
import { SESSION_KEYS } from "@/lib/inbody";

const imgInBody270 = "/upload/inbody-270.png";
const imgInBody570 = "/upload/inbody-570.png";
const imgCamera = "/upload/camera-icon.svg";
const imgUpload = "/upload/upload-icon.svg";

type SheetType = "inbody_270" | "inbody_570";

const SHEETS: { value: SheetType; label: string; caption: string; thumb: string }[] = [
  {
    value: "inbody_270",
    label: "InBody 270",
    caption: "Standard body composition analysis",
    thumb: imgInBody270,
  },
  {
    value: "inbody_570",
    label: "InBody 570",
    caption: "Detailed body composition analysis",
    thumb: imgInBody570,
  },
];

export default function Upload() {
  const [sheetType, setSheetType] = useState<SheetType>("inbody_570");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    saveJSON(SESSION_KEYS.sheetType, sheetType);
  }, [sheetType]);

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="px-[30px] pt-[80px]">
        <h1 className="text-[24px] font-bold text-[#fcfcfc]">Choose your InBody report</h1>
        <p className="mt-2 text-[12px] tracking-[0.02em] text-[#fcfcfc]">
          Select the type of InBody sheet you have. Make sure you choose the correct type
          before uploading your report.
        </p>

        <div className="mt-[15px] flex gap-[9px]">
          {SHEETS.map((sheet) => (
            <button
              key={sheet.value}
              type="button"
              onClick={() => setSheetType(sheet.value)}
              className={`flex-1 overflow-hidden rounded-[15px] bg-white text-left ${
                sheetType === sheet.value ? "border-[5px] border-[#117d69]" : ""
              }`}
            >
              <div className="relative h-[151px] w-full">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt={`${sheet.label} sample sheet`}
                  className="size-full object-cover"
                  src={sheet.thumb}
                />
                {sheetType === sheet.value && (
                  <span className="absolute right-2 top-2 flex size-4 items-center justify-center rounded-full bg-[#117d69] text-[9px] text-white">
                    ✓
                  </span>
                )}
              </div>
              <div className="px-3 py-2 text-center">
                <p className="text-[10px] font-bold text-black">{sheet.label}</p>
                <p className="text-[6px] text-black opacity-60">{sheet.caption}</p>
              </div>
            </button>
          ))}
        </div>

        <h2 className="mt-9 text-[24px] font-bold text-[#fcfcfc]">Upload your report</h2>
        <p className="mt-2 text-[12px] tracking-[0.02em] text-[#fcfcfc]">
          Upload a clear photo or file of your InBody sheet. Make sure all numbers and
          sections are visible.
        </p>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="mt-[15px] flex h-[99px] w-full flex-col items-center justify-center gap-1 rounded-[15px] border-4 border-[#eaeaea] bg-white"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-8" src={imgUpload} />
          <span className="text-[12px] font-medium text-black opacity-50">
            Upload from device
          </span>
        </button>
        <input ref={fileInputRef} type="file" accept="image/*,.pdf" className="hidden" />
        <p className="mt-2 text-right text-[8px] font-bold tracking-[0.02em] text-white opacity-80">
          Supported formats: JPG, PNG, PDF
        </p>

        <Link
          href="/upload/capture"
          className="mt-6 flex h-[40px] w-full items-center justify-center gap-[10px] rounded-lg bg-[#117d69] text-[14px] font-bold tracking-[0.02em] text-white"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-4" src={imgCamera} />
          Open Camera and Take Photo
        </Link>
      </div>
    </PhoneFrame>
  );
}
