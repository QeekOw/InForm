"use client";

// Upload — built to Figma frame "Upload" (node 2054:328).

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import PhotoConfirm from "@/components/PhotoConfirm";
import { usePrivacyGate } from "@/components/PrivacyNotice";
import { btn, Modal } from "@/components/ui";
import { useAuth } from "@/lib/AuthProvider";
import { API_URL } from "@/lib/config";
import { type Capabilities, type ReadJob, type SampleExtraction, type SampleSheetMeta } from "@/lib/inbody";
import { createPdfDataUrl, fileToDataUrl } from "@/lib/photo";
import { clearSheet, loadJSON, removeSessionItem, saveJSON, SESSION_KEYS } from "@/lib/session";

const imgInBody270 = "/upload/inbody-270.png";

/** Light card used by the drop zone and the sample tiles (Figma: 4px #eaeaea border). */
const tileClass =
  "rounded-[15px] border-4 border-[#eaeaea] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] text-black";

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
  const [busy, setBusy] = useState(false);
  const [pickError, setPickError] = useState<string | null>(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [stagedPhoto, setStagedPhoto] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [viewing, setViewing] = useState<SampleSheetMeta | null>(null);
  // null while the probe is in flight; own-photo actions stay off until the
  // server confirms it can read a photo.
  const [liveReadAvailable, setLiveReadAvailable] = useState<boolean | null>(null);

  // One-shot reason left by a screen that redirected here.
  useEffect(() => {
    const handedOver = loadJSON<string>(SESSION_KEYS.notice);
    if (handedOver) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNotice(handedOver);
      removeSessionItem(SESSION_KEYS.notice);
    }
  }, []);

  // A failed probe counts as "no": better to withhold an action than offer one that can't work.
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/capabilities`)
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
      })
      .then((caps: Capabilities) => {
        if (!cancelled) setLiveReadAvailable(caps.live_read_available === true);
      })
      .catch(() => {
        if (!cancelled) setLiveReadAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/samples`)
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
      })
      .then((data: SampleSheetMeta[]) => {
        if (!cancelled && Array.isArray(data)) setSamples(data);
      })
      .catch(() => {
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
    setBusy(true);
    try {
      if (liveReadAvailable === true) {
        // Run the model on the sample sheet.
        const res = await fetch(`${API_URL}/reads`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sample_id: sample.id, live: true }),
        });
        if (!res.ok) throw new Error(res.statusText);
        const job: ReadJob = await res.json();
        clearSheet();
        saveJSON(SESSION_KEYS.sampleId, sample.id);
        saveJSON(SESSION_KEYS.readId, job.read_id);
        saveJSON(SESSION_KEYS.photo, `${API_URL}${sample.image_url}`);
        router.push(`/upload/analyzing?read_id=${job.read_id}&live=1`);
      } else {
        // No model here: use the stored read, and always review it first.
        const res = await fetch(`${API_URL}/samples/${sample.id}`);
        if (!res.ok) throw new Error(res.statusText);
        const extraction: SampleExtraction = await res.json();
        clearSheet();
        saveJSON(SESSION_KEYS.sampleId, sample.id);
        saveJSON(SESSION_KEYS.extraction, extraction);
        saveJSON(SESSION_KEYS.photo, `${API_URL}${sample.image_url}`);
        saveJSON(SESSION_KEYS.reading, extraction.status === "complete" && extraction.data ? extraction.data : null);
        router.push("/preview");
      }
    } catch (err) {
      console.error("Error opening sample:", err);
      setPickError("Couldn't open that sample. Check your connection and tap it again.");
      setBusy(false);
    }
  };

  // Picking a file only stages it; nothing is sent until "Confirm and Analyze".
  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploadError(null);
    if (file.type.startsWith("image/")) {
      try {
        setStagedPhoto(await fileToDataUrl(file));
      } catch {
        setUploadError("Couldn't open that file. Try a JPG or PNG photo of your sheet.");
      }
    } else if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
      setStagedPhoto(createPdfDataUrl(file.name));
    } else {
      setUploadError("That file type isn't supported. Use a JPG, PNG or PDF.");
    }
  };

  const handleConfirmUpload = async () => {
    if (!stagedPhoto) return;
    clearSheet();
    saveJSON(SESSION_KEYS.photo, stagedPhoto);
    setUploadingPhoto(true);
    setUploadError(null);
    try {
      const res = await fetch(`${API_URL}/reads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: stagedPhoto, live: true }),
      });
      if (!res.ok) throw new Error(res.statusText);
      const job: ReadJob = await res.json();
      saveJSON(SESSION_KEYS.readId, job.read_id);
      router.push(`/upload/analyzing?read_id=${job.read_id}&upload=1`);
    } catch {
      setUploadError("Couldn't start reading this photo. Check your connection and try again.");
      setUploadingPhoto(false);
    }
  };

  const ownPhotoOff = liveReadAvailable !== true;

  return (
    <PhoneFrame bg="bg-gradient-to-b from-[#3e3e3e] to-[#222]">
      <div className="px-[30px] pb-[60px] pt-[48px] text-[#fcfcfc]">
        <BackButton fallbackHref={account ? "/dashboard" : "/"} />

        <h1 className="mt-[26px] text-[24px] font-bold">Upload your InBody 270</h1>
        <p className="mt-[5px] w-[297px] max-w-full text-[12px] leading-[1.5] tracking-[0.02em]">
          Upload a clear photo or file of your InBody 270 sheet. Make sure all numbers and sections
          are visible.
        </p>

        {notice && (
          <p role="status" className="mt-[10px] text-[12px] leading-[1.5] text-[#fcfcfc]/80">
            {notice}
          </p>
        )}

        {/* Drop zone */}
        <button
          type="button"
          onClick={() => guard(() => fileInputRef.current?.click())}
          disabled={ownPhotoOff || uploadingPhoto}
          className={`${tileClass} mt-[24px] flex h-[99px] w-full flex-col items-center justify-center transition-[filter] hover:brightness-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf] disabled:cursor-not-allowed disabled:opacity-60`}
        >
          <Icon name="upload" size={32} className="text-[#464646]" />
          <span className="mt-[6px] text-[12px] font-medium text-black/50">
            {liveReadAvailable === null ? "Checking…" : "Upload from device"}
          </span>
        </button>
        <input ref={fileInputRef} type="file" accept="image/*,.pdf" className="hidden" onChange={handleFileSelected} />
        <p className="mt-[5px] text-right text-[8px] font-bold tracking-[0.02em] text-white/80">
          Supported formats: JPG, PNG, PDF
        </p>

        <button
          type="button"
          onClick={() => guard(() => router.push("/upload/capture"))}
          disabled={ownPhotoOff}
          className={`${btn.primary} mt-[20px]`}
        >
          <Icon name="camera" size={16} />
          Open Camera and Take Photo
        </button>

        {liveReadAvailable === false && (
          <p className="mt-[10px] text-[10px] leading-[1.5] text-[#fcfcfc]/70">
            Reading your own sheet isn&apos;t available on this server yet. The samples below
            work end to end.
          </p>
        )}
        {uploadError && !stagedPhoto && (
          <p role="alert" className="mt-[10px] text-[10px] text-[#fcfcfc]/80">
            {uploadError}
          </p>
        )}

        {/* or use */}
        <div className="mt-[32px] flex items-center gap-[16px] text-[10px] font-bold tracking-[0.02em] text-white/80" aria-hidden="true">
          <span className="h-[0.8px] flex-1 bg-white/80" />
          or use
          <span className="h-[0.8px] flex-1 bg-white/80" />
        </div>

        <h2 className="mt-[30px] text-[24px] font-bold">Sample Gallery</h2>
        <p className="mt-[5px] text-[12px] leading-[1.5] tracking-[0.02em]">
          No InBody report? No problem.
          <br />
          Choose our sample to explore how it works.
        </p>

        {loadingList ? (
          <p role="status" className="mt-[20px] text-[12px] text-white/60">
            Loading samples…
          </p>
        ) : listError ? (
          <p role="alert" className="mt-[20px] text-[12px] text-white/80">
            Couldn&apos;t load the samples. The server may be waking up; reload in a moment.
          </p>
        ) : (
          <ul className="mt-[15px] grid grid-cols-2 gap-[15px]">
            {samples.map((sample) => {
              const working = busy && selectedId === sample.id;
              const fallback = sample.source_device === "inbody_270" ? imgInBody270 : null;
              return (
                <li key={sample.id} className="relative">
                  <button
                    type="button"
                    onClick={() => handleSelectSample(sample)}
                    disabled={busy}
                    aria-busy={working}
                    aria-label={`Use sample: ${sample.name}`}
                    className={`${tileClass} flex h-[255px] w-full flex-col p-[6px] transition-[filter] hover:brightness-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7ee0cf] disabled:cursor-wait ${
                      selectedId === sample.id ? "border-[#117d69]" : ""
                    }`}
                  >
                    <span className="relative block h-[204px] w-full overflow-hidden rounded-[4px] bg-zinc-200">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        alt=""
                        src={`${API_URL}${sample.image_url}`}
                        className="size-full object-cover object-top"
                        onError={(e) => {
                          const img = e.currentTarget;
                          if (fallback && !img.src.endsWith(fallback)) img.src = fallback;
                          else img.style.visibility = "hidden";
                        }}
                      />
                      {working && (
                        <span className="absolute inset-0 flex items-center justify-center bg-black/40">
                          <span className="size-6 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        </span>
                      )}
                    </span>
                    <span className="flex flex-1 items-center justify-center px-1 text-center text-[12px] font-bold leading-[1.3] tracking-[0.02em]">
                      {sample.name}
                    </span>
                  </button>
                  {/* Eye: look at the sheet without picking it */}
                  <button
                    type="button"
                    onClick={() => setViewing(sample)}
                    aria-label={`View ${sample.name}`}
                    className="absolute right-[14px] top-[14px] flex size-[24px] items-center justify-center rounded-full bg-[#117d69] text-white shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
                  >
                    <Icon name="eye" size={14} />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {pickError && (
          <p role="alert" className="mt-[10px] text-[10px] text-[#fcfcfc]/80">
            {pickError}
          </p>
        )}
      </div>

      <Modal open={viewing !== null} onClose={() => setViewing(null)} title={viewing?.name ?? ""} widthClass="max-w-[370px]">
        {viewing && (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt={`Sample sheet: ${viewing.name}`} src={`${API_URL}${viewing.image_url}`} className="mt-3 w-full rounded-[8px]" />
            {viewing.description && <p className="mt-3 text-[11px] leading-relaxed text-black/70">{viewing.description}</p>}
            <button
              type="button"
              className={`${btn.primary} mt-4`}
              onClick={() => {
                const s = viewing;
                setViewing(null);
                handleSelectSample(s);
              }}
            >
              Use this sample
            </button>
            <button type="button" className={`${btn.secondary} mt-[8px]`} onClick={() => setViewing(null)}>
              Close
            </button>
          </>
        )}
      </Modal>

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
