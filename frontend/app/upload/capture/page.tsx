"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import { saveJSON } from "@/lib/session";
import { SESSION_KEYS } from "@/lib/inbody";
import { captureFromVideo } from "@/lib/photo";

const imgShutterOuter = "/icons/camera/shutter-outer.svg";
const imgShutterInner = "/icons/camera/shutter-inner.svg";
const imgFlash = "/icons/camera/flash-button.svg";
const imgGallery = "/icons/camera/gallery-button.svg";
const imgBack = "/icons/camera/back-arrow.svg";

type CameraState = "requesting" | "ready" | "denied" | "unsupported";

export default function Capture() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("requesting");

  useEffect(() => {
    let cancelled = false;

    if (!navigator.mediaDevices?.getUserMedia) {
      // Feature detection of a browser-only external API, not derived state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState("unsupported");
      return;
    }

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
      .catch(() => setState("denied"));

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const handleCapture = () => {
    if (state !== "ready" || !videoRef.current) return;
    const dataUrl = captureFromVideo(videoRef.current);
    saveJSON(SESSION_KEYS.photo, dataUrl);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    router.push("/upload/analyzing");
  };

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <div className="absolute inset-x-0 top-8 bottom-6 flex items-center justify-center overflow-hidden bg-black">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`size-full object-cover ${state === "ready" ? "" : "hidden"}`}
        />
        {state === "requesting" && (
          <p className="px-10 text-center text-[12px] text-white/40">Starting camera…</p>
        )}
        {(state === "denied" || state === "unsupported") && (
          <div className="px-10 text-center text-[12px] text-white/70">
            <p>
              {state === "denied"
                ? "Camera access was denied."
                : "This browser can't access the camera."}
            </p>
            <Link href="/upload" className="mt-2 inline-block underline">
              Upload from device instead
            </Link>
          </div>
        )}
      </div>

      <Link
        href="/upload"
        className="absolute left-[30px] top-[61px] flex size-8 items-center justify-center rounded-full bg-white shadow-md"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="Back" className="size-[18px]" src={imgBack} />
      </Link>

      <div className="absolute left-[61px] top-[562px] flex h-[53px] w-[280px] items-center justify-center rounded-[15px] border border-[#309487] bg-[#117d6999] px-4">
        <p className="text-center text-[12px] font-bold tracking-[0.02em] text-white">
          Make sure the report is well-lit, fully visible, and easy to read.
        </p>
      </div>

      <div className="absolute inset-x-0 bottom-[52px] flex items-center justify-center">
        <Link
          href="/upload"
          aria-label="Upload from device instead"
          className="absolute left-[62px] size-[42px]"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-full" src={imgGallery} />
        </Link>

        <button
          type="button"
          aria-label="Capture photo"
          onClick={handleCapture}
          disabled={state !== "ready"}
          className="relative block disabled:opacity-40"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-[85px]" src={imgShutterOuter} />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            alt=""
            className="absolute left-1/2 top-1/2 size-[61px] -translate-x-1/2 -translate-y-1/2"
            src={imgShutterInner}
          />
        </button>

        <button
          type="button"
          aria-label="Toggle flash"
          disabled
          className="absolute right-[62px] size-[42px] opacity-40"
          title="Flash control isn't supported across browsers yet"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img alt="" className="size-full" src={imgFlash} />
        </button>
      </div>
    </PhoneFrame>
  );
}
