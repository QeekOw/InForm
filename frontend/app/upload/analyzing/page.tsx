"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import BackButton from "@/components/BackButton";
import PhoneFrame from "@/components/PhoneFrame";
import ReportPhoto from "@/components/ReportPhoto";
import { API_URL } from "@/lib/config";
import { type ReadJob } from "@/lib/inbody";
import { isSubmittableImageData } from "@/lib/photo";
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";

const imgScanLine = "/icons/scan/scan-line.svg";

function AnalyzingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const paramReadId = searchParams.get("read_id");
  const isLive = searchParams.get("live") === "1";
  const isUpload = searchParams.get("upload") === "1";

  const [readId, setReadId] = useState<string | null>(null);
  // Whether the read id has been looked for yet. Without this, the polling
  // effect below runs once with readId still null â€” before the session lookup
  // has committed â€” and takes the no-read-id branch for a read that is in fact
  // perfectly recoverable.
  const [readIdResolved, setReadIdResolved] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>("Initializing analysis...");
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number>(0);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    /* eslint-disable react-hooks/set-state-in-effect */
    setReadId(paramReadId || loadJSON<string>(SESSION_KEYS.readId));
    setReadIdResolved(true);
    /* eslint-enable react-hooks/set-state-in-effect */
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

    // Wait for the read id lookup above rather than acting on a stale null.
    if (!readIdResolved) return;

    if (!readId) {
      // No read to resume: not in the query param, not in session. The only
      // remaining option is to start a fresh read â€” and only from something
      // that is actually image data. The session photo may be a sample sheet's
      // server URL (stored for side-by-side display), which decodes to garbage
      // and comes back as an unreadable photo (Requirement 1.5).
      const photo = loadJSON<string>(SESSION_KEYS.photo);
      if (isSubmittableImageData(photo)) {
        fetch(`${API_URL}/reads`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image_data: photo, live: true }),
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
            console.error("Failed to start read from photo in session:", err);
            if (!cancelled) {
              saveJSON(
                SESSION_KEYS.notice,
                "We couldn't reach the server to start reading your sheet. Nothing was read, so nothing was guessed. Try again when you're back online.",
              );
              router.replace("/upload");
            }
          });
        return () => {
          cancelled = true;
        };
      }

      // Say what happened instead of inventing a refusal for a sheet that was
      // never read.
      saveJSON(
        SESSION_KEYS.notice,
        "That read was interrupted and couldn't be picked back up â€” the page lost track of it. Nothing was read, so nothing was guessed. Pick a sheet to start again.",
      );
      router.replace("/upload");
      return () => {
        cancelled = true;
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
              // Under Choice 1, all sheets route to /preview for side-by-side review & clarification
              router.push("/preview");
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
          setError("Reconnecting to inference workerâ€¦");
          // Wait 2 seconds before retry on network error
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    }

    pollLoop();

    return () => {
      cancelled = true;
    };
  }, [readId, readIdResolved, router, isUpload]);

  const percent = Math.min(100, Math.max(0, Math.round(progress * 100)));

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      {/* Also the way out of a read taking longer than someone wants to wait;
          the job keeps running server-side either way. */}
      <BackButton href="/upload" label="Stop waiting and go back" className="absolute left-[31px] top-[48px] z-10" />

      <div className="flex min-h-[874px] flex-col items-center px-[30px] pb-[40px] pt-[160px] text-[#fcfcfc]">
        <h1
          className="max-w-[240px] text-center text-[24px] font-bold leading-[1.2] tracking-[0.02em]"
          aria-live="polite"
        >
          Analyzing your body composition...
        </h1>
        <p className="mt-[8px] text-center text-[12px] text-[#fcfcfc]/70">
          {isUpload
            ? "Reading the numbers off your photo"
            : isLive
              ? "Reading the sample sheet with the model"
              : "Reading your sheet"}
        </p>

        <div className="relative mt-[34px] h-[370px] w-[265px] overflow-hidden rounded-[15px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] p-[10px] shadow-[0_4px_16px_rgba(0,0,0,0.25)]">
          <div className="relative size-full overflow-hidden rounded-[8px] bg-[#1f1f1f]">
            <ReportPhoto />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img alt="" className="absolute inset-x-0 w-full animate-scan" src={imgScanLine} />
          </div>
        </div>

        {/* Honest progress: a real percentage, not an endless spinner */}
        <div className="mt-[30px] w-full" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label="Reading progress">
          <div className="flex items-center justify-between text-[12px]">
            <span className="font-bold text-[#7ee0cf]">{message}</span>
            <span className="font-mono font-bold">{percent}%</span>
          </div>
          <div className="mt-2 h-[6px] w-full overflow-hidden rounded-full bg-white/15">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#117d69] to-[#2dd4bf] transition-all duration-300 ease-out"
              style={{ width: `${percent}%` }}
            />
          </div>
          <p className="mt-2 text-[10px] text-white/50">
            {elapsed}s elapsed{isLive || isUpload ? " · usually 10–45 seconds" : ""}
          </p>
        </div>

        {error && <p className="mt-2 text-center text-[11px] text-rose-300">{error}</p>}
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
            Loadingâ€¦
          </div>
        </PhoneFrame>
      }
    >
      <AnalyzingContent />
    </Suspense>
  );
}
