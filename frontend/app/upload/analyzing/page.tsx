"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { API_URL } from "@/lib/config";
import { isCleanRead, type ReadJob } from "@/lib/inbody";
import type { SheetSource } from "@/lib/photo";
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";

const imgScanLine = "/icons/scan/scan-line.svg";

function AnalyzingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const paramReadId = searchParams.get("read_id");
  const isLive = searchParams.get("live") === "1";
  const isUpload = searchParams.get("upload") === "1";

  const [readId, setReadId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>("Initializing analysis...");
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number>(0);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReadId(paramReadId || loadJSON<string>(SESSION_KEYS.readId));
  }, [paramReadId]);

  // Elapsed seconds timer for honest feedback
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!readId) {
      const photo = loadJSON<string>(SESSION_KEYS.photo);
      if (photo) {
        // Automatically start reading the uploaded sheet in session if read_id is missing
        const source = loadJSON<SheetSource>(SESSION_KEYS.sheetSource) ?? "photo";
        fetch(`${API_URL}/reads`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image_data: photo, live: true, source }),
        })
          .then((res) => {
            if (!res.ok) throw new Error("Failed to start reading");
            return res.json();
          })
          .then((job: ReadJob) => {
            if (!cancelled) {
              saveJSON(SESSION_KEYS.readId, job.read_id);
              setReadId(job.read_id);
            }
          })
          .catch((err) => {
            console.error("Failed to start read from the sheet in session:", err);
            if (!cancelled) router.push("/preview");
          });
        return () => {
          cancelled = true;
        };
      }

      const timer = setTimeout(() => {
        if (!cancelled) router.push("/preview");
      }, 3000);
      return () => {
        cancelled = true;
        clearTimeout(timer);
      };
    }

    // Long polling loop that survives free-host request timeouts
    async function pollLoop() {
      while (!cancelled) {
        try {
          // Poll with a 10s server timeout to avoid host gateway cutoffs
          const res = await fetch(`${API_URL}/reads/${readId}?timeout=10`);
          if (!res.ok) {
            throw new Error(`Server returned ${res.status}`);
          }
          const job: ReadJob = await res.json();
          if (cancelled) break;

          setProgress(job.progress);
          if (job.message) setMessage(job.message);

          if (job.status === "complete") {
            const extraction = job.extraction;
            if (extraction && extraction.data) {
              saveJSON(SESSION_KEYS.reading, extraction.data);
            } else {
              saveJSON(SESSION_KEYS.reading, null);
            }
            if (extraction) {
              saveJSON(SESSION_KEYS.extraction, extraction);
            }
            saveJSON(SESSION_KEYS.readId, job.read_id);

            // Brief pause at 100% so user sees completion before transition
            await new Promise((r) => setTimeout(r, 600));
            if (!cancelled) {
              // Uploaded photos MUST go to preview for side-by-side review (ADR-0011)
              const sampleId = loadJSON<string>(SESSION_KEYS.sampleId);
              const isUserUpload = isUpload || !sampleId;
              router.push(isUserUpload || !extraction || !isCleanRead(extraction) ? "/preview" : "/result");
            }
            break;
          } else if (job.status === "refused") {
            const extraction = job.extraction;
            saveJSON(SESSION_KEYS.reading, null);
            if (extraction) {
              saveJSON(SESSION_KEYS.extraction, extraction);
            }
            saveJSON(SESSION_KEYS.readId, job.read_id);

            await new Promise((r) => setTimeout(r, 600));
            if (!cancelled) {
              router.push("/preview");
            }
            break;
          }

          // If still pending, loop continues next poll immediately
        } catch (err) {
          console.error("Polling error, retrying...", err);
          setError("Reconnecting to inference worker…");
          // Wait 2 seconds before retry on network error
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    }

    pollLoop();

    return () => {
      cancelled = true;
    };
  }, [readId, router, isUpload]);

  const percent = Math.min(100, Math.max(0, Math.round(progress * 100)));

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="flex h-full flex-col justify-between px-6 pt-12 pb-8">
        <div>
          <h1 className="text-center text-[22px] font-bold text-[#fcfcfc]">
            {isUpload
              ? "Analyzing your uploaded sheet..."
              : isLive
              ? "Running Live Inference..."
              : "Analyzing your sheet..."}
          </h1>
          <p className="mt-1 text-center text-[12px] text-white/70">
            {isUpload
              ? "Extracting body composition parameters from your sheet"
              : isLive
              ? "Self-hosted Donut model running on CPU (~45s expected)"
              : "Extracting body composition parameters"}
          </p>

          <div className="relative mx-auto mt-6 h-[260px] w-[210px] overflow-hidden rounded-[15px] border-4 border-[#117d69] bg-[#1f1f1f] shadow-lg">
            <ReportPhoto />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="absolute inset-x-0 w-full animate-scan" src={imgScanLine} />
          </div>
        </div>

        {/* Honest Progress Display (No indeterminate spinner) */}
        <div className="mt-4 rounded-xl border border-white/10 bg-black/30 p-4 backdrop-blur-xs">
          <div className="flex items-center justify-between text-[12px]">
            <span className="font-semibold text-emerald-400">{message}</span>
            <span className="font-mono font-bold text-white">{percent}%</span>
          </div>

          {/* Real linear progress bar */}
          <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-white/15">
            <div
              className="h-full rounded-full bg-[#117d69] transition-all duration-300 ease-out"
              style={{ width: `${percent}%` }}
            />
          </div>

          <div className="mt-3 flex items-center justify-between text-[10px] text-white/50">
            <span>Elapsed: {elapsed}s</span>
            <span>{isLive ? "Estimated progress (~45s on CPU)" : "Instant"}</span>
          </div>
        </div>

        {error && (
          <div className="mt-2 text-center text-[11px] text-rose-300">
            {error}
          </div>
        )}
      </div>
    </PhoneFrame>
  );
}

export default function Analyzing() {
  return (
    <Suspense
      fallback={
        <PhoneFrame bg="bg-[#3e3e3e]">
          <div className="flex h-full items-center justify-center text-white text-[14px]">
            Loading…
          </div>
        </PhoneFrame>
      }
    >
      <AnalyzingContent />
    </Suspense>
  );
}
