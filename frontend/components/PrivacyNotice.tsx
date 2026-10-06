"use client";

import { useCallback, useState } from "react";
import { loadJSON, saveJSON, SESSION_KEYS } from "@/lib/session";
import Icon from "./Icon";
import { btn, Modal } from "./ui";

/**
 * Gate an action (upload, camera) behind the Student Project & Privacy Notice.
 *
 * `guard(action)` runs `action` straight away once the notice has been
 * acknowledged this session; otherwise it opens the notice and runs `action`
 * after the person ticks the box and presses Continue.
 */
export function usePrivacyGate() {
  const [pending, setPending] = useState<(() => void) | null>(null);

  const guard = useCallback((action: () => void) => {
    if (loadJSON<boolean>(SESSION_KEYS.privacyAck)) {
      action();
      return;
    }
    // Wrapped so React stores the function instead of calling it as an updater.
    setPending(() => action);
  }, []);

  const notice = (
    <PrivacyNoticeDialog
      open={pending !== null}
      onCancel={() => setPending(null)}
      onContinue={() => {
        saveJSON(SESSION_KEYS.privacyAck, true);
        const action = pending;
        setPending(null);
        action?.();
      }}
    />
  );

  return { guard, notice };
}

function PrivacyNoticeDialog({
  open,
  onCancel,
  onContinue,
}: {
  open: boolean;
  onCancel: () => void;
  onContinue: () => void;
}) {
  const [agreed, setAgreed] = useState(false);

  return (
    <Modal
      open={open}
      onClose={() => {
        setAgreed(false);
        onCancel();
      }}
      widthClass="max-w-[291px]"
      title={<span className="text-[16px]">Student Project and Privacy Notice</span>}
      icon={<span aria-hidden="true" className="text-[16px]">⚠️</span>}
    >
      <div className="mt-[14px] space-y-2 text-[11px] leading-[1.45] text-black/80">
        <p>
          InForm is an academic student research prototype. When you upload or photograph your
          InBody sheet:
        </p>
        <ul className="list-disc space-y-1 pl-4">
          <li>
            <strong>Temporary session only:</strong> your photo is held in memory during this
            session only, so you can check the extracted numbers side by side.
          </li>
          <li>
            <strong>Zero persistence:</strong> your photo is never written to a database, cloud
            storage, disk, or logs.
          </li>
          <li>
            <strong>Discarded on save:</strong> once you confirm or save your scan, the photo is
            permanently discarded. Only your verified numbers are used for your plan.
          </li>
        </ul>
      </div>

      <label className="mt-5 flex cursor-pointer items-start gap-[10px] text-[11px] font-bold leading-snug">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
          className="mt-[1px] size-[16px] shrink-0 accent-[#117d69]"
        />
        I&apos;ve read and understood the Student Project and Privacy Notice.
      </label>

      <button
        type="button"
        className={`${btn.primary} mt-5`}
        disabled={!agreed}
        onClick={() => {
          setAgreed(false);
          onContinue();
        }}
      >
        Continue
        <Icon name="arrowRight" size={16} />
      </button>
    </Modal>
  );
}
