"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import PhotoConfirm from "@/components/PhotoConfirm";
import { usePrivacyGate } from "@/components/PrivacyNotice";
import { btn, cardClass, OrDivider, Tag } from "@/components/ui";
import { useAuth } from "@/lib/AuthProvider";
import { API_URL } from "@/lib/config";
import {
  type Capabilities,
  type ReadJob,
  type SampleExtraction,
  type SampleSheetMeta,
} from "@/lib/inbody";
import { createPdfDataUrl, fileToDataUrl } from "@/lib/photo";
import { clearSheet, loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "@/lib/session";

const imgInBody270 = "/upload/inbody-270.png";

export default function Upload() {
  const router = useRouter();
  const { account } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Own photos only: the notice is about what happens to *your* sheet, so the
  // sample gallery isn't gated.
  const { guard, notice: privacyNotice } = usePrivacyGate();

  const [samples, setSamples] = useState<SampleSheetMeta[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadingSample, setLoadingSample] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);
  const [startingLiveRead, setStartingLiveRead] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [stagedPhoto, setStagedPhoto] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // null while the probe is in flight; the live-read action stays unavailable
  // until the server confirms it can actually perform it.
  const [liveReadAvailable, setLiveReadAvailable] = useState<boolean | null>(null);

  // A screen that redirected here leaves its reason behind, so someone bounced
  // back to the gallery is told why rather than left guessing. One-shot: read it
  // and drop it, so a later reload doesn't replay a stale explanation.
  useEffect(() => {
    const handedOver = loadJSON<string>(SESSION_KEYS.notice);
    if (handedOver) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNotice(handedOver);
      removeSessionItem(SESSION_KEYS.notice);
    }
  }, []);

  // Ask the server whether it can run the model on demand (Requirement 1.6).
  // A failed probe is treated as "no": better to withhold the action than to
  // offer one that cannot succeed.
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/capabilities`)
      .then((res) => {
        if (!res.ok) throw new Error(`Capability probe failed: ${res.statusText}`);
        return res.json();
      })
      .then((caps: Capabilities) => {
        if (!cancelled) setLiveReadAvailable(caps.live_read_available === true);
      })
      .catch((err) => {
        console.error("Failed to probe server capabilities:", err);
        if (!cancelled) setLiveReadAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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

  const handleSelectSample = async (sample: SampleSheetMeta) => {
    setSelectedId(sample.id);
    setPickError(null);

    // If live reading is available, run the live AI model on the sample sheet
    if (liveReadAvailable === true) {
      setStartingLiveRead(true);
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

        router.push(`/upload/analyzing?read_id=${job.read_id}&live=1`);
      } catch (err) {
        console.error("Error starting live read:", err);
        setPickError("Failed to initiate live model reading. Please try again.");
      } finally {
        setStartingLiveRead(false);
      }
    } else {
      // Fallback if model isn't installed: load stored sample extraction, but ALWAYS go to /preview
      setLoadingSample(true);
      try {
        const res = await fetch(`${API_URL}/samples/${sample.id}`);
        if (!res.ok) {
          throw new Error(`Failed to load sample extraction: ${res.statusText}`);
        }
        const extraction: SampleExtraction = await res.json();

        clearSheet();
        saveJSON(SESSION_KEYS.sampleId, sample.id);
        saveJSON(SESSION_KEYS.extraction, extraction);
        saveJSON(SESSION_KEYS.photo, `${API_URL}${sample.image_url}`);

        if (extraction.status === "complete" && extraction.data) {
          saveJSON(SESSION_KEYS.reading, extraction.data);
        } else {
          saveJSON(SESSION_KEYS.reading, null);
        }

        // Under Choice 1, all sheets always route to /preview for review & clarification
        router.push("/preview");
      } catch (err) {
        console.error("Error loading sample:", err);
        setPickError("Couldn't load that sheet. Check your connection and tap it again.");
      } finally {
        setLoadingSample(false);
      }
    }
  };

  // Picking a file only stages it: the person sees it full-size first and
  // nothing is sent until "Confirm and Analyze" (Figma "Preview").
  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset so picking the same file again after "Choose other file" still fires.
    e.target.value = "";
    if (!file) return;
    setUploadError(null);

    let photoDataUrl = "";
    if (file.type.startsWith("image/")) {
      try {
        photoDataUrl = await fileToDataUrl(file);
      } catch (err) {
        console.error("Error converting file to data URL:", err);
        setUploadError("Couldn't open that file. Try a JPG or PNG photo of your sheet.");
        return;
      }
    } else if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
      photoDataUrl = createPdfDataUrl(file.name);
    } else {
      setUploadError("That file type isn't supported. Use a JPG, PNG or PDF.");
      return;
    }
    setStagedPhoto(photoDataUrl);
  };

  const handleConfirmUpload = async () => {
    const photoDataUrl = stagedPhoto;
    if (!photoDataUrl) return;
    clearSheet();
    saveJSON(SESSION_KEYS.photo, photoDataUrl);
    setUploadingPhoto(true);
    setUploadError(null);

    try {
      const res = await fetch(`${API_URL}/reads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: photoDataUrl, live: true }),
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

  const busy = startingLiveRead || loadingSample;

  return (
    <PhoneFrame bg="bg-[#3e3e3e]" scrollable>
      <div className="px-[30px] pb-[60px] pt-[54px] text-[#fcfcfc]">
        <div className="flex items-center justify-between">
          <BackButton fallbackHref={account ? "/dashboard" : "/"} />
          {account && (
            <Link href="/dashboard" className="text-[12px] font-bold text-[#7ee0cf] hover:underline">
              Dashboard
            </Link>
          )}
        </div>

        {notice && (
          <div
            role="status"
            className="mt-4 flex items-start gap-2 rounded-[8px] border border-amber-400/40 bg-amber-500/15 p-3 text-[11px] leading-relaxed text-amber-100"
          >
            <Icon name="alert" size={14} className="mt-[1px]" />
            <p>{notice}</p>
          </div>
        )}

        <h1 className="mt-[26px] text-[24px] font-bold tracking-[0.02em]">Upload your InBody 270</h1>
        <p className="mt-[5px] text-[12px] leading-[1.5] text-[#fcfcfc]/90">
          Upload a clear photo or file of your InBody 270 sheet. Make sure all numbers and sections
          are visible.
        </p>

        {liveReadAvailable === false ? (
          // Reading your own sheet needs the model. Say so before anyone goes
          // and finds their sheet, not after they've uploaded it.
          <div className={`${cardClass} mt-[24px] p-[20px] text-[12px] leading-relaxed`}>
            <p className="font-bold">Reading your own sheet isn&apos;t available here yet</p>
            <p className="mt-1.5 text-black/75">
              The model needed to read your sheet isn&apos;t installed on this server. Rather than
              let you take a photo that nothing can read, we&apos;re telling you now.
            </p>
            <p className="mt-2 text-black/60">
              The sample sheets below give the full experience: flagged values, corrections,
              calorie targets, exercises and the dashboard all work from them.
            </p>
          </div>
        ) : (
          <>
            <button
              type="button"
              onClick={() => guard(() => fileInputRef.current?.click())}
              disabled={uploadingPhoto || liveReadAvailable === null}
              className="mt-[24px] flex h-[114px] w-full flex-col items-center justify-center rounded-[15px] border-2 border-dashed border-[#fcfcfc]/50 bg-[#fcfcfc]/5 transition-colors hover:bg-[#fcfcfc]/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf] disabled:opacity-50"
            >
              <Icon name="upload" size={32} />
              <span className="mt-[6px] text-[12px] font-bold">
                {uploadingPhoto
                  ? "Starting analysis…"
                  : liveReadAvailable === null
                    ? "Checking the reader is available…"
                    : "Upload from device"}
              </span>
              <span className="mt-[14px] self-end pr-[12px] text-[8px] text-[#fcfcfc]/70">
                Supported formats: JPG, PNG, PDF
              </span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf"
              className="hidden"
              onChange={handleFileSelected}
            />

            <button
              type="button"
              onClick={() => guard(() => router.push("/upload/capture"))}
              disabled={liveReadAvailable === null}
              className={`${btn.primary} mt-[15px]`}
            >
              <Icon name="camera" size={16} />
              Open Camera and Take Photo
            </button>
          </>
        )}

        {uploadError && (
          <p role="alert" className="mt-3 text-[12px] text-rose-300">
            {uploadError}
          </p>
        )}

        <div className="my-[32px] text-[#fcfcfc]">
          <OrDivider label="Or use" />
        </div>

        <h2 className="text-[24px] font-bold tracking-[0.02em]">Sample Gallery</h2>
        <p className="mt-[5px] text-[12px] leading-[1.5] text-[#fcfcfc]/90">
          No InBody report? No problem. Choose one of our samples to explore how it works.
        </p>

        {loadingList ? (
          <p className="mt-4 text-[12px] text-white/60">Loading sample sheets…</p>
        ) : listError ? (
          <p role="alert" className="mt-4 text-[12px] text-rose-300">
            Couldn&apos;t load the sample sheets. The server may be starting up; reload the page in
            a moment.
          </p>
        ) : samples.length === 0 ? (
          <p className="mt-4 text-[12px] text-white/60">No sample sheets available.</p>
        ) : (
          <ul className="mt-[15px] grid grid-cols-2 gap-[12px]">
            {samples.map((sample) => {
              const isSelected = selectedId === sample.id;
              const isWorking = isSelected && busy;
              const fallbackThumb = sample.source_device === "inbody_270" ? imgInBody270 : null;
              return (
                <li key={sample.id}>
                  <button
                    type="button"
                    onClick={() => handleSelectSample(sample)}
                    disabled={busy}
                    aria-busy={isWorking}
                    className={`${cardClass} flex h-full w-full flex-col overflow-hidden p-[8px] text-left transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf] disabled:cursor-wait ${
                      isSelected ? "ring-[3px] ring-[#117d69]" : "hover:ring-2 hover:ring-white/50"
                    }`}
                  >
                    <div className="relative h-[120px] w-full overflow-hidden rounded-[8px] bg-zinc-200">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        alt=""
                        className="size-full object-cover object-top"
                        src={`${API_URL}${sample.image_url}`}
                        onError={(e) => {
                          const img = e.currentTarget;
                          if (fallbackThumb && !img.src.endsWith(fallbackThumb)) img.src = fallbackThumb;
                          else img.style.visibility = "hidden";
                        }}
                      />
                      <span className="absolute left-[6px] top-[6px]">
                        <Tag tone={sample.provenance === "synthetic" ? "sky" : "teal"} className="shadow-sm">
                          {sample.provenance === "synthetic" ? "Synthetic" : "Real printout"}
                        </Tag>
                      </span>
                      {isWorking && (
                        <span className="absolute inset-0 flex items-center justify-center bg-black/40">
                          <span className="size-6 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        </span>
                      )}
                    </div>
                    <span className="mt-[8px] text-[12px] font-bold leading-tight">{sample.name}</span>
                    <span className="mt-[3px] line-clamp-2 text-[9px] leading-snug text-black/60">
                      {sample.description}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {pickError && (
          <p role="alert" className="mt-3 text-[12px] text-rose-300">
            {pickError}
          </p>
        )}
      </div>
      {privacyNotice}
      {stagedPhoto && (
        <PhotoConfirm
          photo={stagedPhoto}
          busy={uploadingPhoto}
          error={uploadError}
          onBack={() => {
            setStagedPhoto(null);
            setUploadError(null);
          }}
          alternateLabel="Choose other file"
          alternateIcon="image"
          onAlternate={() => fileInputRef.current?.click()}
          onConfirm={handleConfirmUpload}
        />
      )}
    </PhoneFrame>
  );
}
