"use client";

// Per-value status markers, following the Figma "exclamation" component: a
// small green circle beside the number, and (for warnings) a green speech
// bubble with the explanation when tapped. Edited/checked use the same circle
// with a different glyph so every marker shares one visual language.

import { useEffect, useId, useRef, useState } from "react";
import Icon from "./Icon";

const circle =
  "flex size-[16px] shrink-0 items-center justify-center rounded-full bg-[#5cbfa8] text-white";

export const FLAG_MESSAGE =
  "This number may have been read incorrectly. Please compare it with your original InBody report.";

/**
 * Green "!" marker. Tap (or focus + Enter) to show the bubble. When `message`
 * describes an error that must be fixed, pass `open` to show it straight away.
 */
export function FlagMarker({
  label,
  message = FLAG_MESSAGE,
  open: forcedOpen = false,
  align = "right",
}: {
  /** Name of the value, for the accessible label. */
  label: string;
  message?: string;
  /** Keep the bubble visible (used for values that can't be accepted). */
  open?: boolean;
  /** Which side the bubble's tail sits on. */
  align?: "left" | "right";
}) {
  const [toggled, setToggled] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const bubbleId = useId();
  const open = forcedOpen || toggled;

  useEffect(() => {
    if (!toggled) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent) {
        if (e.key === "Escape") setToggled(false);
        return;
      }
      if (!ref.current?.contains(e.target as Node)) setToggled(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [toggled]);

  return (
    <span ref={ref} className="relative inline-flex">
      <button
        type="button"
        onClick={() => setToggled((v) => !v)}
        aria-label={`${label}: ${message}`}
        aria-expanded={open}
        aria-describedby={open ? bubbleId : undefined}
        className={`${circle} focus:outline-none focus-visible:ring-2 focus-visible:ring-white`}
      >
        <span aria-hidden="true" className="text-[11px] font-bold leading-none">
          !
        </span>
      </button>
      {open && (
        <span
          id={bubbleId}
          role="status"
          className={`absolute top-[22px] z-20 w-[196px] rounded-[9px] border-2 border-[#117d69] bg-[rgba(17,125,105,0.95)] px-[11px] py-[8px] text-left text-[10px] font-medium leading-[1.4] text-[#fcfcfc] shadow-lg ${
            align === "right" ? "right-[-6px]" : "left-[-6px]"
          }`}
        >
          {message}
        </span>
      )}
    </span>
  );
}

/** The "!" circle without its own popover, for rows whose message is already shown inline. */
export function FlagDot() {
  return (
    <span className={circle} aria-hidden="true">
      <span className="text-[11px] font-bold leading-none">!</span>
    </span>
  );
}

/** Same circle, check glyph: a flagged value the person compared and kept. */
export function CheckedMarker() {
  return (
    <span className={circle} title="Checked by you" role="img" aria-label="Checked by you">
      <Icon name="check" size={11} />
    </span>
  );
}

/** Same circle, pencil glyph: a value the person typed in. */
export function EditedMarker() {
  return (
    <span className={circle} title="Edited by you" role="img" aria-label="Edited by you">
      <Icon name="pencil" size={9} />
    </span>
  );
}

/** One line explaining the edited/checked markers, shown only when used. */
export function MarkerLegend({ edited, checked }: { edited: boolean; checked: boolean }) {
  if (!edited && !checked) return null;
  return (
    <p className="mt-[14px] flex flex-wrap items-center gap-x-[14px] gap-y-1 text-[10px] text-[#fcfcfc]/70">
      {edited && (
        <span className="flex items-center gap-[6px]">
          <EditedMarker /> Edited by you
        </span>
      )}
      {checked && (
        <span className="flex items-center gap-[6px]">
          <CheckedMarker /> Checked by you
        </span>
      )}
    </p>
  );
}

/**
 * The Figma "Flagged notification" bubble, laid out in the flow under the row
 * it belongs to (so several can be visible without overlapping). Used for a
 * value that can't be accepted until it's fixed.
 */
export function NoteBubble({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <p
      id={id}
      role="alert"
      className="relative ml-auto mt-[8px] w-[196px] max-w-full rounded-[9px] border-2 border-[#117d69] bg-[rgba(17,125,105,0.9)] px-[11px] py-[8px] text-[10px] font-medium leading-[1.4] text-[#fcfcfc]"
    >
      {/* tail pointing up at the value */}
      <span
        aria-hidden="true"
        className="absolute -top-[6px] right-[24px] size-[10px] rotate-45 border-l-2 border-t-2 border-[#117d69] bg-[rgba(17,125,105,0.9)]"
      />
      {children}
    </p>
  );
}
