"use client";

import Icon, { type IconName } from "./Icon";
import { btn } from "./ui";

/**
 * Full-screen "is this the photo you meant?" step between picking or taking a
 * photo and sending it to be read (Figma "Preview"). Nothing is sent until
 * Confirm and Analyze is pressed.
 */
export default function PhotoConfirm({
  photo,
  onConfirm,
  onAlternate,
  alternateLabel,
  alternateIcon,
  onBack,
  busy = false,
  error,
}: {
  photo: string;
  onConfirm: () => void;
  /** Retake (camera) or Choose other file (upload). */
  onAlternate: () => void;
  alternateLabel: string;
  alternateIcon: IconName;
  onBack: () => void;
  busy?: boolean;
  error?: string | null;
}) {
  return (
    <div className="fixed inset-y-0 left-1/2 z-40 flex w-full max-w-[402px] -translate-x-1/2 flex-col bg-[#3e3e3e] px-[30px] pb-[48px] pt-[48px]">
      <button
        type="button"
        onClick={onBack}
        disabled={busy}
        aria-label="Back"
        className="inline-flex h-[28px] w-[75px] items-center justify-center gap-[5px] self-start rounded-[60px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] text-[12px] font-bold tracking-[0.04em] text-black shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#117d69]"
      >
        <Icon name="arrowLeft" size={16} />
        <span aria-hidden="true">back</span>
      </button>

      <div className="mt-[32px] min-h-0 flex-1 overflow-hidden rounded-[15px] bg-black/30">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img alt="The photo you're about to send" src={photo} className="size-full object-contain" />
      </div>

      {error && (
        <p role="alert" className="mt-3 text-center text-[12px] text-rose-300">
          {error}
        </p>
      )}

      <button type="button" onClick={onAlternate} disabled={busy} className={`${btn.light} mt-[23px] text-black`}>
        <Icon name={alternateIcon} size={16} className="text-[#117d69]" />
        {alternateLabel}
      </button>
      <button type="button" onClick={onConfirm} disabled={busy} className={`${btn.primary} mt-[10px]`}>
        {busy ? "Sending…" : "Confirm and Analyze"}
        {!busy && <Icon name="arrowRight" size={16} />}
      </button>
    </div>
  );
}
