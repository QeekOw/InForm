"use client";

// Shared building blocks for the Figma redesign. Before this, every page
// copy-pasted the same card/button/input classes. Tokens follow the Figma file:
// light gradient cards, teal gradient primary buttons, translucent grey inputs.

import { useEffect, useId, useRef, useState } from "react";
import Icon, { type IconName } from "./Icon";

// --- Class tokens -----------------------------------------------------------

const btnBase =
  "flex h-[40px] w-full items-center justify-center gap-[10px] rounded-[8px] px-[10px] text-[14px] font-bold tracking-[0.02em] transition-[opacity,filter] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#117d69] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export const btn = {
  /** Teal gradient, the main action on a screen. */
  primary: `${btnBase} bg-gradient-to-b from-[#117d69] to-[#116e5d] text-[#fcfcfc] shadow-sm hover:brightness-110`,
  /** Light grey, a neutral alternative (Google, Cancel, Retake). */
  secondary: `${btnBase} bg-[#eaeaea] text-black hover:brightness-95`,
  /** White card-style button on dark screens (Edit, Discard, Choose other file). */
  light: `${btnBase} bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] text-[#117d69] shadow-sm hover:brightness-95`,
  /** Translucent teal, the soft alternative (Continue as a Guest). */
  soft: `${btnBase} bg-gradient-to-b from-[rgba(17,125,105,0.21)] to-[rgba(8,81,67,0.21)] text-[#117d69] hover:brightness-95`,
  /** Destructive confirm in a dialog. */
  danger: `${btnBase} bg-gradient-to-b from-[#c0392b] to-[#a93226] text-white shadow-sm hover:brightness-110`,
};

export const cardClass =
  "rounded-[15px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] text-black shadow-[0_4px_16px_rgba(0,0,0,0.18)]";

/** Shared input shell so text inputs and selects line up exactly. */
const inputShell =
  "h-[35px] w-full rounded-[8px] border border-[#d9d9d9] bg-[rgba(217,217,217,0.5)] text-[12px] text-black placeholder:text-black/50 focus:border-[#117d69] focus:outline-none focus:ring-1 focus:ring-[#117d69]";

// --- Layout -----------------------------------------------------------------

export function Card({
  children,
  className = "",
  as: Tag = "div",
}: {
  children: React.ReactNode;
  className?: string;
  as?: "div" | "section" | "form" | "article";
}) {
  return <Tag className={`${cardClass} ${className}`}>{children}</Tag>;
}

/** A full-bleed photo behind a dark gradient, as on the auth and result screens. */
export function PhotoBackdrop({
  src,
  className = "absolute inset-0",
  fade = "from-[rgba(62,62,62,0.7)] to-[rgba(34,34,34,0.7)]",
}: {
  src: string;
  className?: string;
  /** Tailwind gradient stops for the overlay. */
  fade?: string;
}) {
  return (
    <div aria-hidden="true" className={`pointer-events-none overflow-hidden ${className}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img alt="" src={src} className="size-full object-cover" />
      <div className={`absolute inset-0 bg-gradient-to-b ${fade}`} />
    </div>
  );
}

/** Small teal pill, used for exercise types and status labels. */
export function Tag({
  children,
  tone = "teal",
  className = "",
}: {
  children: React.ReactNode;
  tone?: "teal" | "amber" | "rose" | "sky";
  className?: string;
}) {
  const tones = {
    teal: "bg-[#117d69]/20 text-[#0b5e4f]",
    amber: "bg-amber-200 text-amber-900",
    rose: "bg-rose-200 text-rose-900",
    sky: "bg-sky-200 text-sky-900",
  };
  return (
    <span
      className={`inline-flex items-center rounded-[4px] px-[6px] py-[2px] text-[9px] font-bold ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

// --- Form fields --------------------------------------------------------------

type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "className">;

export function FieldLabel({ htmlFor, children }: { htmlFor?: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-[7px] block text-[12px] tracking-[0.02em] text-black">
      {children}
    </label>
  );
}

export function FieldError({ id, children }: { id?: string; children?: React.ReactNode }) {
  if (!children) return null;
  return (
    <p id={id} role="alert" className="mt-1 text-[10px] font-medium text-rose-700">
      {children}
    </p>
  );
}

/** Labelled text input with an optional leading icon and trailing slot. */
export function TextField({
  label,
  icon,
  trailing,
  error,
  hint,
  ...input
}: InputProps & {
  label: string;
  icon?: IconName;
  trailing?: React.ReactNode;
  error?: string | null;
  hint?: React.ReactNode;
}) {
  const autoId = useId();
  const id = input.id ?? autoId;
  const errorId = `${id}-error`;
  return (
    <div>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute left-[15px] top-1/2 -translate-y-1/2 text-[#464646]">
            <Icon name={icon} size={16} />
          </span>
        )}
        <input
          {...input}
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={`${inputShell} ${icon ? "pl-[41px]" : "pl-[15px]"} ${trailing ? "pr-[40px]" : "pr-[15px]"}`}
        />
        {trailing && (
          <span className="absolute right-[12px] top-1/2 flex -translate-y-1/2 items-center">
            {trailing}
          </span>
        )}
      </div>
      {hint}
      <FieldError id={errorId}>{error}</FieldError>
    </div>
  );
}

/** Password input with its own show/hide toggle (each field toggles independently). */
export function PasswordField(props: Omit<InputProps, "type"> & {
  label: string;
  error?: string | null;
  hint?: React.ReactNode;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <TextField
      {...props}
      type={visible ? "text" : "password"}
      icon="lock"
      trailing={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? `Hide ${props.label.toLowerCase()}` : `Show ${props.label.toLowerCase()}`}
          aria-pressed={visible}
          className="rounded p-[2px] text-[#464646] hover:text-black focus:outline-none focus-visible:ring-2 focus-visible:ring-[#117d69]"
        >
          <Icon name={visible ? "eyeOff" : "eye"} size={16} />
        </button>
      }
    />
  );
}

/** Native select styled like the inputs, with the Figma caret. */
export function SelectField({
  label,
  value,
  onChange,
  placeholder,
  options,
  error,
  id: givenId,
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  options: { value: string; label: string }[];
  error?: string | null;
  id?: string;
  required?: boolean;
}) {
  const autoId = useId();
  const id = givenId ?? autoId;
  return (
    <div>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <div className="relative">
        <select
          id={id}
          value={value}
          required={required}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={error ? true : undefined}
          className={`${inputShell} appearance-none pl-[15px] pr-[36px] ${value ? "" : "text-black/50"}`}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((o) => (
            <option key={o.value} value={o.value} className="text-black">
              {o.label}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-[12px] top-1/2 -translate-y-1/2 text-[#464646]">
          <Icon name="caretDown" size={16} />
        </span>
      </div>
      <FieldError>{error}</FieldError>
    </div>
  );
}

/** Horizontal radio group (Biological Sex). */
export function RadioGroup<T extends string>({
  label,
  name,
  value,
  onChange,
  options,
}: {
  label: string;
  name: string;
  value: T | null;
  onChange: (value: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <fieldset>
      <legend className="mb-[10px] text-[12px] tracking-[0.02em] text-black">{label}</legend>
      <div className="flex gap-[60px]">
        {options.map((o) => {
          const checked = value === o.value;
          return (
            <label key={o.value} className="flex cursor-pointer items-center gap-[10px] text-[12px] font-bold">
              <input
                type="radio"
                name={name}
                value={o.value}
                checked={checked}
                onChange={() => onChange(o.value)}
                className="peer sr-only"
              />
              <span
                aria-hidden="true"
                className={`flex size-[16px] items-center justify-center rounded-full border-2 border-[#117d69] peer-focus-visible:ring-2 peer-focus-visible:ring-[#117d69] peer-focus-visible:ring-offset-1`}
              >
                {checked && <span className="size-[8px] rounded-full bg-[#117d69]" />}
              </span>
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/** Stacked option cards (Goals): the picked one gets the teal outline. */
export function OptionCards<T extends string>({
  label,
  name,
  value,
  onChange,
  options,
}: {
  label: string;
  name: string;
  value: T | null;
  onChange: (value: T) => void;
  options: { value: T; label: string; icon: IconName }[];
}) {
  return (
    <fieldset>
      <legend className="mb-[7px] text-[12px] tracking-[0.02em] text-black">{label}</legend>
      <div className="flex flex-col gap-[5px]">
        {options.map((o) => {
          const checked = value === o.value;
          return (
            <label
              key={o.value}
              className={`flex h-[35px] cursor-pointer items-center gap-[10px] rounded-[8px] border px-[15px] text-[12px] transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[#117d69] ${
                checked
                  ? "border-2 border-[#117d69] bg-[rgba(217,217,217,0.5)] font-bold"
                  : "border-[#d9d9d9] bg-[rgba(217,217,217,0.5)]"
              }`}
            >
              <input
                type="radio"
                name={name}
                value={o.value}
                checked={checked}
                onChange={() => onChange(o.value)}
                className="sr-only"
              />
              <Icon name={o.icon} size={16} />
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

// --- Dialog -------------------------------------------------------------------

/**
 * Centered dialog over a dimmed backdrop. Escape and a backdrop click call
 * `onClose` (unless `dismissible` is false); focus moves into the dialog on open
 * and returns to whatever had it on close.
 */
export function Modal({
  open,
  onClose,
  title,
  icon,
  children,
  dismissible = true,
  widthClass = "max-w-[319px]",
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  icon?: React.ReactNode;
  children: React.ReactNode;
  dismissible?: boolean;
  widthClass?: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(
      "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])",
    );
    (first ?? panel)?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dismissible) onClose();
      if (e.key === "Tab" && panel) {
        // Keep Tab inside the dialog.
        const focusables = Array.from(
          panel.querySelectorAll<HTMLElement>(
            "button:not([disabled]), [href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex='-1'])",
          ),
        );
        if (focusables.length === 0) return;
        const firstEl = focusables[0];
        const lastEl = focusables[focusables.length - 1];
        if (e.shiftKey && document.activeElement === firstEl) {
          e.preventDefault();
          lastEl.focus();
        } else if (!e.shiftKey && document.activeElement === lastEl) {
          e.preventDefault();
          firstEl.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previouslyFocused?.focus?.();
    };
  }, [open, dismissible, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-5 backdrop-blur-[2px]"
      onMouseDown={(e) => {
        if (dismissible && e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`${cardClass} max-h-[90vh] w-full overflow-y-auto p-[25px] focus:outline-none ${widthClass}`}
      >
        <h2 id={titleId} className="flex items-start justify-center gap-2 text-center text-[20px] font-bold leading-tight">
          {icon}
          <span>{title}</span>
        </h2>
        {children}
      </div>
    </div>
  );
}

/** Two-button confirm dialog (Discard, Delete account, Sign out, Discard changes). */
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  cancelLabel = "Cancel",
  confirmIcon,
  destructive = true,
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: React.ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  confirmIcon?: IconName;
  destructive?: boolean;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal open={open} onClose={busy ? () => {} : onCancel} title={title} dismissible={!busy}>
      <p className="mt-3 text-center text-[12px] leading-relaxed text-black/70">{body}</p>
      {error && <p role="alert" className="mt-3 text-center text-[11px] font-medium text-rose-700">{error}</p>}
      <div className="mt-6 flex gap-[9px]">
        <button type="button" className={btn.secondary} onClick={onCancel} disabled={busy}>
          {cancelLabel}
        </button>
        <button
          type="button"
          className={destructive ? btn.danger : btn.primary}
          onClick={onConfirm}
          disabled={busy}
        >
          {confirmIcon && <Icon name={confirmIcon} size={16} />}
          {busy ? "Working…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}

/** "or" divider between button groups. */
export function OrDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="flex items-center gap-[16px] text-[10px] text-current opacity-60" aria-hidden="true">
      <span className="h-px flex-1 bg-current" />
      {label}
      <span className="h-px flex-1 bg-current" />
    </div>
  );
}

/** The Google "G" built from the existing four-part logo SVGs. */
export function GoogleLogo() {
  return (
    <span className="relative size-[16px]" aria-hidden="true">
      {[1, 2, 3, 4].map((n) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={n} alt="" src={`/icons/auth/google-${n}.svg`} className="absolute inset-0 size-full" />
      ))}
    </span>
  );
}
