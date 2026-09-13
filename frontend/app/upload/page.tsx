"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import { saveJSON } from "@/lib/session";
import {
  DEFAULT_READING,
  DEFAULT_SAMPLES,
  SESSION_KEYS,
  type InBodyReading,
  type SampleExtraction,
  type SampleSheetMeta,
} from "@/lib/inbody";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const imgCamera = "/upload/camera-icon.svg";
const imgUpload = "/upload/upload-icon.svg";
const imgInBody270 = "/upload/inbody-270.png";
const imgInBody570 = "/upload/inbody-570.png";

export default function Upload() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [samples, setSamples] = useState<SampleSheetMeta[]>(DEFAULT_SAMPLES);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadingSample, setLoadingSample] = useState(false);
  const [refusalBanner, setRefusalBanner] = useState<{
    id: string;
    name: string;
    message: string;
  } | null>(null);

  // Fetch live manifest from backend on mount; fallback to DEFAULT_SAMPLES
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/samples`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: SampleSheetMeta[] | null) => {
        if (!cancelled && data && Array.isArray(data) && data.length > 0) {
          setSamples(data);
        }
      })
      .catch(() => {
        // Offline or backend not yet reached: DEFAULT_SAMPLES used
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handlePickSample = async (sample: SampleSheetMeta) => {
    setSelectedId(sample.id);
    setLoadingSample(true);
    setRefusalBanner(null);

    try {
      const res = await fetch(`${API_URL}/samples/${sample.id}`);
      let extraction: SampleExtraction | null = null;
      if (res.ok) {
        extraction = await res.json();
      }

      if (!extraction) {
        // Fallback for offline/demo if API is unreachable
        if (sample.id === "refused_non_sheet") {
          extraction = {
            status: "refused",
            data: null,
            unread: ["weight_kg", "lean_body_mass_kg"],
            flagged: [],
            error: "missing_required_fields",
            message:
              "Could not confidently read required fields. Please re-upload a clearer photo.",
          };
        } else {
          extraction = {
            status: "complete",
            data: {
              ...DEFAULT_READING,
              source_device: sample.source_device ?? "inbody_270",
            },
            unread: [],
            flagged: sample.id.includes("flagged") ? ["lean_body_mass_kg"] : [],
          };
        }
      }

      saveJSON(SESSION_KEYS.sampleId, sample.id);
      saveJSON(SESSION_KEYS.extraction, extraction);

      if (extraction.status === "complete" && extraction.data) {
        const fullReading: InBodyReading = {
          ...DEFAULT_READING,
          ...extraction.data,
          source_device: extraction.data.source_device ?? sample.source_device ?? "inbody_270",
          segmental_lean: {
            ...DEFAULT_READING.segmental_lean,
            ...(extraction.data.segmental_lean ?? {}),
          },
        };
        saveJSON(SESSION_KEYS.reading, fullReading);
        router.push("/preview");
      } else if (extraction.status === "refused") {
        setRefusalBanner({
          id: sample.id,
          name: sample.name,
          message:
            extraction.message ??
            "The model refused this document because required InBody fields could not be identified.",
        });
      }
    } catch {
      // Fallback transition
      router.push("/preview");
    } finally {
      setLoadingSample(false);
    }
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      router.push("/upload/analyzing");
    }
  };

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="max-h-screen overflow-y-auto px-[24px] pt-[50px] pb-[80px]">
        {/* Title */}
        <h1 className="text-[24px] font-bold text-[#fcfcfc]">Select an InBody sheet</h1>
        
        {/* Short line explaining what an InBody sheet is (Acceptance Criteria #5) */}
        <div className="mt-3 rounded-xl border border-emerald-500/30 bg-[#117d69]/15 p-3 text-[12px] leading-relaxed text-[#fcfcfc]">
          <span className="font-bold text-[#2dd4bf]">What is an InBody sheet?</span> An InBody
          sheet is a body composition printout that breaks down total weight into skeletal muscle,
          body fat, and body water using bioelectrical impedance analysis.
        </div>

        {/* Refusal Banner Alert (when a refused sample is selected) */}
        {refusalBanner && (
          <div className="mt-4 rounded-xl border border-rose-500/50 bg-rose-950/70 p-4 text-[#fcfcfc]">
            <div className="flex items-center gap-2">
              <span className="rounded bg-rose-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                Fail-Closed Refusal
              </span>
              <span className="text-[12px] font-semibold">{refusalBanner.name}</span>
            </div>
            <p className="mt-2 text-[11px] leading-normal text-rose-200">
              {refusalBanner.message}
            </p>
            <p className="mt-2 text-[10px] text-rose-300/80 italic">
              Our model declines to predict rather than hallucinating numbers on non-sheet or illegible inputs.
            </p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => router.push("/preview")}
                className="rounded-lg bg-rose-600 px-3 py-1.5 text-[11px] font-bold text-white shadow-sm hover:bg-rose-500"
              >
                Inspect refusal in Preview →
              </button>
              <button
                type="button"
                onClick={() => setRefusalBanner(null)}
                className="rounded-lg border border-white/20 px-3 py-1.5 text-[11px] text-white/80"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Sample Gallery Section */}
        <div className="mt-5">
          <div className="flex items-baseline justify-between">
            <h2 className="text-[16px] font-bold text-[#fcfcfc]">Sample Gallery</h2>
            <span className="text-[11px] text-emerald-400 font-medium">Instant pre-computed reads</span>
          </div>
          <p className="mt-1 text-[11px] text-white/70">
            Pick any sheet to see its stored extraction immediately without waiting on the model.
          </p>

          <div className="mt-3 flex flex-col gap-3">
            {samples.map((sample) => {
              const isSelected = selectedId === sample.id;
              const isRefusal = sample.id === "refused_non_sheet";
              const isFlagged = sample.id.includes("flagged");

              // Choose local preview image fallback
              const fallbackThumb = sample.id.includes("570") ? imgInBody570 : imgInBody270;
              const imgSource = `${API_URL}${sample.image_url}`;

              return (
                <button
                  key={sample.id}
                  type="button"
                  onClick={() => handlePickSample(sample)}
                  disabled={loadingSample && isSelected}
                  className={`group flex overflow-hidden rounded-[14px] bg-white p-3 text-left transition-all ${
                    isSelected
                      ? "ring-4 ring-[#117d69] shadow-lg"
                      : "hover:ring-2 hover:ring-white/40"
                  }`}
                >
                  {/* Thumbnail */}
                  <div className="relative h-[90px] w-[70px] shrink-0 overflow-hidden rounded-lg bg-zinc-200">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      alt={sample.name}
                      className="size-full object-cover"
                      src={imgSource}
                      onError={(e) => {
                        // Fallback to bundled thumbnail if backend image endpoint is loading
                        (e.currentTarget as HTMLImageElement).src = fallbackThumb;
                      }}
                    />
                    {isSelected && (
                      <span className="absolute right-1 top-1 flex size-4 items-center justify-center rounded-full bg-[#117d69] text-[9px] text-white font-bold">
                        ✓
                      </span>
                    )}
                  </div>

                  {/* Metadata */}
                  <div className="ml-3 flex flex-1 flex-col justify-between">
                    <div>
                      {/* Badges: Provenance & Behavior */}
                      <div className="flex flex-wrap gap-1">
                        {sample.provenance === "synthetic" ? (
                          <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[9px] font-bold text-sky-800">
                            Synthetic
                          </span>
                        ) : (
                          <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[9px] font-bold text-emerald-900">
                            Real Printout (Consented)
                          </span>
                        )}

                        {isRefusal ? (
                          <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[9px] font-bold text-rose-800">
                            Refused
                          </span>
                        ) : isFlagged ? (
                          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[9px] font-bold text-amber-800">
                            Flagged Check
                          </span>
                        ) : (
                          <span className="rounded bg-teal-100 px-1.5 py-0.5 text-[9px] font-bold text-teal-800">
                            Clean Read
                          </span>
                        )}
                      </div>

                      <h3 className="mt-1 text-[12px] font-bold text-zinc-900 leading-tight">
                        {sample.name}
                      </h3>
                      <p className="mt-1 text-[10px] text-zinc-600 line-clamp-2 leading-snug">
                        {sample.description}
                      </p>
                    </div>

                    <div className="mt-1 text-[10px] font-semibold text-[#117d69]">
                      {isSelected && loadingSample
                        ? "Loading extraction…"
                        : "Tap to inspect stored extraction →"}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Divider / Or Upload Your Own Sheet */}
        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-white/20" />
          <span className="text-[11px] font-semibold tracking-wider uppercase text-white/50">
            Or Use Your Own Sheet
          </span>
          <div className="h-px flex-1 bg-white/20" />
        </div>

        <div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex h-[75px] w-full flex-col items-center justify-center gap-1 rounded-[15px] border-2 border-dashed border-white/30 bg-white/5 hover:bg-white/10 transition-colors"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-6 opacity-70" src={imgUpload} />
            <span className="text-[11px] font-medium text-white/80">
              Upload from photo library (JPG, PNG, PDF)
            </span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf"
            className="hidden"
            onChange={handleFileSelected}
          />

          <Link
            href="/upload/capture"
            className="mt-3 flex h-[38px] w-full items-center justify-center gap-[8px] rounded-lg bg-[#117d69] text-[13px] font-bold text-white shadow-sm"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-4" src={imgCamera} />
            Take Photo with Camera
          </Link>
        </div>
      </div>
    </PhoneFrame>
  );
}
