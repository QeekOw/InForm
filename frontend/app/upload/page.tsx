"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import { API_URL } from "@/lib/config";
import { isCleanRead, type ReadJob, type SampleExtraction, type SampleSheetMeta } from "@/lib/inbody";
import { fileToSheetImage, type SheetImage, SheetPickError } from "@/lib/photo";
import { clearSheet, saveJSON, SESSION_KEYS } from "@/lib/session";

const imgCamera = "/upload/camera-icon.svg";
const imgUpload = "/upload/upload-icon.svg";
const imgInBody270 = "/upload/inbody-270.png";

export default function Upload() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [samples, setSamples] = useState<SampleSheetMeta[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadingSample, setLoadingSample] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);
  const [scepticModalSample, setScepticModalSample] = useState<SampleSheetMeta | null>(null);
  const [startingLiveRead, setStartingLiveRead] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Fetch live manifest from backend on mount
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/samples`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load sample manifest: ${res.statusText}`);
        return res.json();
      })
      .then((data: SampleSheetMeta[]) => {
        if (!cancelled && Array.isArray(data)) {
          setSamples(data);
        }
      })
      .catch((err) => {
        console.error("Failed to load sample manifest:", err);
        if (!cancelled) setListError(true);
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handlePickSample = async (sample: SampleSheetMeta) => {
    setSelectedId(sample.id);
    setLoadingSample(true);
    setPickError(null);

    try {
      const res = await fetch(`${API_URL}/samples/${sample.id}`);
      if (!res.ok) {
        throw new Error(`Failed to load sample extraction: ${res.statusText}`);
      }
      const extraction: SampleExtraction = await res.json();

      clearSheet();
      saveJSON(SESSION_KEYS.sampleId, sample.id);
      saveJSON(SESSION_KEYS.extraction, extraction);

      if (extraction.status === "complete" && extraction.data) {
        saveJSON(SESSION_KEYS.reading, extraction.data);
      } else {
        // Fail-closed (ADR-0008): never store fabricated numbers for a refused sheet
        saveJSON(SESSION_KEYS.reading, null);
      }

      // A clean read goes straight to results with no extra taps; anything
      // unread, flagged or refused stops at the preview for a person.
      router.push(isCleanRead(extraction) ? "/result" : "/preview");
    } catch (err) {
      console.error("Error loading sample:", err);
      setPickError("Couldn't load that sheet. Check your connection and tap it again.");
    } finally {
      setLoadingSample(false);
    }
  };

  const handleStartLiveRead = async (sample: SampleSheetMeta) => {
    setStartingLiveRead(true);
    setPickError(null);

    try {
      const res = await fetch(`${API_URL}/reads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_id: sample.id, live: true }),
      });
      if (!res.ok) {
        throw new Error(`Failed to start live read: ${res.statusText}`);
      }
      const job: ReadJob = await res.json();

      clearSheet();
      saveJSON(SESSION_KEYS.sampleId, sample.id);
      saveJSON(SESSION_KEYS.readId, job.read_id);
      saveJSON(SESSION_KEYS.photo, `${API_URL}${sample.image_url}`);

      setScepticModalSample(null);
      router.push(`/upload/analyzing?read_id=${job.read_id}&live=1`);
    } catch (err) {
      console.error("Error starting live read:", err);
      setPickError("Failed to initiate live model reading. Please try again.");
    } finally {
      setStartingLiveRead(false);
    }
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target;
    const file = input.files?.[0];
    if (!file) return;

    // Cleared so picking the same file again after a refusal still fires
    // `change` and gets another go.
    input.value = "";

    clearSheet();
    setUploadingPhoto(true);
    setUploadError(null);

    let sheet: SheetImage;
    try {
      sheet = await fileToSheetImage(file);
    } catch (err) {
      // The file never became image data, so say why rather than letting the
      // backend call it an unreadable photo.
      setUploadError(
        err instanceof SheetPickError
          ? err.message
          : "Could not read that file. Try a photo of the sheet instead.",
      );
      setUploadingPhoto(false);
      return;
    }

    saveJSON(SESSION_KEYS.photo, sheet.dataUrl);
    saveJSON(SESSION_KEYS.sheetPages, sheet.pageCount);

    try {
      const res = await fetch(`${API_URL}/reads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: sheet.dataUrl, live: true }),
      });

      if (!res.ok) {
        throw new Error(`Failed to start reading: ${res.statusText}`);
      }

      const job: ReadJob = await res.json();
      saveJSON(SESSION_KEYS.readId, job.read_id);
      router.push(`/upload/analyzing?read_id=${job.read_id}&upload=1`);
    } catch (err) {
      console.error("Error initiating read for uploaded sheet:", err);
      setUploadError("Could not start analyzing this photo. Check your connection and try again.");
      setUploadingPhoto(false);
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

        {/* Sample Gallery Section */}
        <div className="mt-5">
          <div className="flex items-baseline justify-between">
            <h2 className="text-[16px] font-bold text-[#fcfcfc]">Sample Gallery</h2>
            <span className="text-[11px] text-emerald-400 font-medium">Instant pre-computed reads</span>
          </div>
          <p className="mt-1 text-[11px] text-white/70">
            Pick any sheet to see its stored extraction immediately without waiting on the model.
          </p>

          {loadingList ? (
            <p className="mt-4 text-[12px] text-white/60">Loading sample sheets…</p>
          ) : listError ? (
            <p role="alert" className="mt-4 text-[12px] text-rose-300">
              Couldn&apos;t load the sample sheets. The server may be starting up; reload the page
              in a moment.
            </p>
          ) : samples.length === 0 ? (
            <p className="mt-4 text-[12px] text-white/60">No sample sheets available.</p>
          ) : (
            <div className="mt-3 flex flex-col gap-3">
              {samples.map((sample) => {
                const isSelected = selectedId === sample.id;
                // Only the 270 has a bundled fallback thumbnail; others hide on error.
                const fallbackThumb = sample.source_device === "inbody_270" ? imgInBody270 : null;
                const imgSource = `${API_URL}${sample.image_url}`;

                return (
                  <div
                    key={sample.id}
                    className={`overflow-hidden rounded-[14px] bg-white p-3 text-left transition-all ${
                      isSelected
                        ? "ring-4 ring-[#117d69] shadow-lg"
                        : "hover:ring-2 hover:ring-white/40"
                    }`}
                  >
                    {/* Primary clickable area: instant pre-computed reading */}
                    <button
                      type="button"
                      onClick={() => handlePickSample(sample)}
                      disabled={loadingSample && isSelected}
                      className="group flex w-full text-left"
                    >
                      {/* Thumbnail */}
                      <div className="relative h-[90px] w-[70px] shrink-0 overflow-hidden rounded-lg bg-zinc-200">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          alt={sample.name}
                          className="size-full object-cover"
                          src={imgSource}
                          onError={(e) => {
                            const img = e.currentTarget as HTMLImageElement;
                            if (fallbackThumb && !img.src.endsWith(fallbackThumb)) {
                              img.src = fallbackThumb;
                            } else {
                              img.style.display = "none";
                            }
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
                          {/* Honest Provenance Badge Only */}
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
                            : "Tap for instant stored read →"}
                        </div>
                      </div>
                    </button>

                    {/* Sceptic's Button: Clearly visible secondary action (Issue #40) */}
                    <div className="mt-2.5 border-t border-zinc-100 pt-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setScepticModalSample(sample);
                        }}
                        disabled={loadingSample || startingLiveRead}
                        className="flex w-full items-center justify-between rounded-lg border border-emerald-600/30 bg-emerald-50/60 px-2.5 py-1.5 text-[10px] font-medium text-emerald-900 hover:bg-emerald-100/80 transition-colors"
                      >
                        <span className="flex items-center gap-1">
                          <span className="font-bold text-emerald-700">⚡ Sceptic&apos;s button:</span>
                          <span className="underline decoration-emerald-600/40">Run model live</span>
                        </span>
                        <span className="rounded bg-emerald-200/90 px-1.5 py-0.5 font-mono text-[9px] font-bold text-emerald-950">
                          ~45s wait
                        </span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {pickError && (
            <p role="alert" className="mt-3 text-[12px] text-rose-300">
              {pickError}
            </p>
          )}
        </div>

        {/* Divider / Or Upload Your Own Sheet */}
        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-white/20" />
          <span className="text-[11px] font-semibold tracking-wider uppercase text-white/50">
            Or Use Your Own Sheet
          </span>
          <div className="h-px flex-1 bg-white/20" />
        </div>

        {/* Student Project and Privacy Notice (Issue #45 / ADR-0011) */}
        <div className="mb-4 rounded-xl border border-emerald-500/40 bg-emerald-950/40 p-3.5 text-[11px] leading-relaxed text-zinc-200">
          <div className="flex items-center gap-2 font-bold text-emerald-300 text-[12px]">
            <span>🎓 Student Project &amp; Privacy Notice</span>
          </div>
          <p className="mt-1.5 text-zinc-300">
            InForm is an academic student research prototype. When you upload or photograph your InBody sheet:
          </p>
          <ul className="mt-1.5 list-disc pl-4 space-y-1 text-zinc-300">
            <li>
              <strong>Temporary session only:</strong> Your photo is held in memory during this session only so you can review extracted numbers side-by-side.
            </li>
            <li>
              <strong>Zero persistence:</strong> Your photo is <strong>never</strong> written to a database, cloud storage, disk, or logs (ADR-0011).
            </li>
            <li>
              <strong>Discarded on save:</strong> Once you confirm or save your scan, the photo is permanently discarded. Only your verified numbers are used for your plan.
            </li>
          </ul>
        </div>

        <div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingPhoto}
            className="flex h-[75px] w-full flex-col items-center justify-center gap-1 rounded-[15px] border-2 border-dashed border-white/30 bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-50"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-6 opacity-70" src={imgUpload} />
            <span className="text-[11px] font-medium text-white/80">
              {uploadingPhoto
                ? "Starting model analysis…"
                : "Upload from photo library (JPG, PNG, PDF)"}
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
            className="mt-3 flex h-[38px] w-full items-center justify-center gap-[8px] rounded-lg bg-[#117d69] text-[13px] font-bold text-white shadow-sm hover:bg-[#0e6857] transition-colors"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="size-4" src={imgCamera} />
            Take Photo with Camera
          </Link>

          {uploadError && (
            <p role="alert" className="mt-3 text-[12px] text-rose-300">
              {uploadError}
            </p>
          )}
        </div>
      </div>

      {/* Sceptic's Button Confirmation Modal (Issue #40: Upfront wait commitment) */}
      {scepticModalSample && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs">
          <div className="w-full max-w-[330px] rounded-2xl border border-white/20 bg-zinc-900 p-5 text-white shadow-2xl">
            <div className="flex items-center gap-2 text-emerald-400">
              <span className="text-xl">⚡</span>
              <h3 className="text-[16px] font-bold">The Sceptic&apos;s Button</h3>
            </div>

            <p className="mt-2 text-[12px] leading-relaxed text-zinc-300">
              Run our self-hosted <strong>Donut engine</strong> live on{" "}
              <span className="font-semibold text-white">{scepticModalSample.name}</span> rather
              than serving the pre-computed reading.
            </p>

            {/* Expected wait stated up front before committing (AC #2) */}
            <div className="mt-3.5 rounded-xl border border-amber-400/40 bg-amber-500/15 p-3 text-[11px] text-amber-200">
              <p className="flex items-center gap-1 font-bold text-amber-300">
                <span>⏱️ Expected wait:</span>
                <span className="underline">around 45 seconds</span>
              </p>
              <p className="mt-1 text-[10px] leading-normal text-amber-200/90">
                Inference runs live on CPU. It uses long polling so your read survives host timeouts,
                with honest stage-by-stage progress.
              </p>
            </div>

            <p className="mt-3 text-[11px] text-zinc-400">
              The live read will return the exact same audited numbers as the stored reading.
            </p>

            <div className="mt-5 flex gap-2">
              <button
                type="button"
                onClick={() => setScepticModalSample(null)}
                disabled={startingLiveRead}
                className="flex-1 rounded-lg bg-zinc-800 py-2.5 text-[12px] font-semibold text-zinc-300 hover:bg-zinc-700 transition"
              >
                Keep Instant Read
              </button>
              <button
                type="button"
                onClick={() => handleStartLiveRead(scepticModalSample)}
                disabled={startingLiveRead}
                className="flex-1 rounded-lg bg-[#117d69] py-2.5 text-[12px] font-bold text-white hover:bg-[#0e6857] shadow-sm transition"
              >
                {startingLiveRead ? "Starting…" : "Run Live Read (~45s)"}
              </button>
            </div>
          </div>
        </div>
      )}
    </PhoneFrame>
  );
}
