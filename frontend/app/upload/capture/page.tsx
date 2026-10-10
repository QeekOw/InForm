"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import PhotoConfirm from "@/components/PhotoConfirm";
import { btn } from "@/components/ui";
import { API_URL } from "@/lib/config";
import { type ReadJob } from "@/lib/inbody";
import { captureFromVideo } from "@/lib/photo";
import { clearSheet, loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";

type CameraState = "requesting" | "ready" | "denied" | "unsupported";

export default function Capture() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("requesting");
  const [captured, setCaptured] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  // Reachable directly by URL, so it checks for itself rather than trusting
  // that whoever linked here already did.
  const [liveReadAvailable, setLiveReadAvailable] = useState<boolean | null>(null);

  // The Privacy Notice is shown on the upload screen before the camera opens.
  // Anyone arriving here by URL without having seen it goes back there first.
  useEffect(() => {
    if (!loadJSON<boolean>(SESSION_KEYS.privacyAck)) router.replace("/upload");
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/capabilities`)
      .then((res) => {
        if (!res.ok) throw new Error(`Capability probe failed: ${res.statusText}`);
        return res.json();
      })
      .then((caps: { live_read_available?: boolean }) => {
        if (!cancelled) setLiveReadAvailable(caps.live_read_available === true);
      })
      .catch(() => {
        if (!cancelled) setLiveReadAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const startCamera = useCallback(() => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setState("unsupported");
      return () => {};
    }
    let cancelled = false;
    setState("requesting");
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("denied");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    // Starting a browser-only device stream, not derived state.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    const cancel = startCamera();
    return () => {
      cancel();
      stopCamera();
    };
  }, [startCamera, stopCamera]);

  const handleCapture = () => {
    if (state !== "ready" || !videoRef.current || liveReadAvailable !== true) return;
    setCaptured(captureFromVideo(videoRef.current));
    setSendError(null);
    stopCamera();
  };

  const handleRetake = () => {
    setCaptured(null);
    setSendError(null);
    startCamera();
  };

  const handleConfirm = async () => {
    if (!captured) return;
    setSending(true);
    setSendError(null);
    clearSheet();
    saveJSON(SESSION_KEYS.photo, captured);
    try {
      const res = await fetch(`${API_URL}/reads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: captured, live: true }),
      });
      if (!res.ok) throw new Error(`Failed to start reading: ${res.statusText}`);
      const job: ReadJob = await res.json();
      saveJSON(SESSION_KEYS.readId, job.read_id);
      router.push(`/upload/analyzing?read_id=${job.read_id}&upload=1`);
    } catch (err) {
      console.error("Error initiating read for captured sheet:", err);
      setSendError("Couldn't send the photo. Check your connection and try again.");
      setSending(false);
    }
  };

  return (
    <PhoneFrame bg="bg-black">
      <div className="absolute inset-0 flex items-center justify-center overflow-hidden bg-black">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          aria-label="Camera viewfinder"
          className={`size-full object-cover ${state === "ready" ? "" : "hidden"}`}
        />
        {state === "requesting" && (
          <p className="px-10 text-center text-[12px] text-white/50">Starting camera…</p>
        )}
        {(state === "denied" || state === "unsupported") && (
          <div className="px-10 text-center text-[12px] text-white/80">
            <p>
              {state === "denied"
                ? "Camera access was denied. Allow it in your browser settings, or upload a file instead."
                : "This browser can't open the camera."}
            </p>
            <Link href="/upload" className={`${btn.primary} mt-4`}>
              Upload from device instead
            </Link>
          </div>
        )}

        {liveReadAvailable === false && (
          <div className="absolute inset-x-6 top-1/2 -translate-y-1/2 rounded-[15px] bg-black/85 p-4 text-center text-[12px] leading-relaxed text-white/85">
            <p className="font-bold text-white">Nothing here could read the photo</p>
            <p className="mt-1.5">
              The model that reads a sheet isn&apos;t installed on this server, so a picture
              wouldn&apos;t get you a plan.
            </p>
            <Link href="/upload" className={`${btn.primary} mt-3`}>
              Use a sample sheet instead
            </Link>
          </div>
        )}
      </div>

      <BackButton href="/upload" screenAligned />

      {/* Bottom control tray */}
      <div className="absolute inset-x-0 bottom-0 h-[234px] bg-gradient-to-t from-black/80 to-black/30" />

      <div className="absolute left-1/2 top-[562px] flex h-[53px] w-[280px] -translate-x-1/2 items-center justify-center rounded-[15px] bg-[#117d69]/70 px-4 backdrop-blur-sm">
        <p className="text-center text-[12px] font-bold tracking-[0.02em] text-white">
          Make sure the report is well-lit, fully visible, and easy to read.
        </p>
      </div>

      <div className="absolute inset-x-0 top-[682px] flex items-center justify-center">
        <Link
          href="/upload"
          aria-label="Upload from device instead"
          className="absolute left-[62px] flex size-[42px] items-center justify-center rounded-full bg-white/25 text-white hover:bg-white/35"
        >
          <Icon name="image" size={24} />
        </Link>

        <button
          type="button"
          aria-label="Take photo"
          onClick={handleCapture}
          disabled={state !== "ready" || liveReadAvailable !== true}
          className="flex size-[85px] items-center justify-center rounded-full border-4 border-white disabled:opacity-40 focus:outline-none focus-visible:ring-4 focus-visible:ring-[#7ee0cf]"
        >
          <span className="size-[61px] rounded-full bg-white" />
        </button>

        {/* Torch control isn't supported consistently across browsers. */}
        <span
          aria-hidden="true"
          title="Flash isn't supported in browsers yet"
          className="absolute right-[62px] flex size-[42px] items-center justify-center rounded-full bg-white/15 text-white/50"
        >
          <Icon name="flash" size={24} />
        </span>
      </div>

      {captured && (
        <PhotoConfirm
          photo={captured}
          busy={sending}
          error={sendError}
          onBack={handleRetake}
          alternateLabel="Retake"
          alternateIcon="camera"
          onAlternate={handleRetake}
          onConfirm={handleConfirm}
        />
      )}
    </PhoneFrame>
  );
}
