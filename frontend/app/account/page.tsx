"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import {
  btn,
  cardClass,
  ConfirmDialog,
  OptionCards,
  PasswordField,
  RadioGroup,
  SelectField,
  TextField,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { deleteAccount, updateCredentials, updateProfile } from "@/lib/auth";
import { ACTIVITY_OPTIONS, GOAL_LABELS, GOAL_OPTIONS, SEX_OPTIONS } from "@/lib/profileOptions";
import { ACTIVITY_LABELS, todayIso, validateDateOfBirth, type BiologicalSex, type FitnessGoal } from "@/lib/user";

const MIN_PASSWORD_LENGTH = 8;
const MAX_NAME_LENGTH = 80;

type Draft = {
  name: string;
  dob: string;
  email: string;
  newPassword: string;
  currentPassword: string;
  sex: BiologicalSex;
  activity: string;
  goal: FitnessGoal;
};

type Errors = Partial<Record<keyof Draft | "form", string>>;

function formatDob(iso: string | null): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });
}

/** Screen header shared by the view and edit modes. */
function Header({ title, back }: { title: string; back: React.ReactNode }) {
  return (
    <header className="flex h-[120px] items-start justify-between bg-gradient-to-b from-black/60 to-transparent px-[30px] pt-[60px]">
      {back}
      <h1 className="text-[24px] font-bold tracking-[0.02em] text-[#fcfcfc]">{title}</h1>
    </header>
  );
}

export default function AccountSettings() {
  const router = useRouter();
  const { account, loading, signOut, refresh } = useAuth();
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [saving, setSaving] = useState(false);
  const [savedNote, setSavedNote] = useState(false);
  const [dialog, setDialog] = useState<null | "signOut" | "delete" | "discard">(null);
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !account) router.replace("/sign-in?redirect=/account");
  }, [account, loading, router]);

  const initialDraft = (): Draft | null =>
    account
      ? {
          name: account.name ?? "",
          dob: account.date_of_birth ?? "",
          email: account.email,
          newPassword: "",
          currentPassword: "",
          sex: account.default_biological_sex ?? "male",
          activity: account.default_activity_multiplier != null ? String(account.default_activity_multiplier) : "",
          goal: account.default_fitness_goal ?? "fat_loss",
        }
      : null;

  const startEditing = () => {
    setDraft(initialDraft());
    setErrors({});
    setSavedNote(false);
    setMode("edit");
  };

  const original = initialDraft();
  const isDirty =
    draft !== null &&
    original !== null &&
    (Object.keys(draft) as (keyof Draft)[]).some((k) => draft[k] !== original[k]);

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
    setErrors((e) => ({ ...e, [key]: undefined, form: undefined }));
  };

  const emailChanged = draft !== null && account !== null && draft.email.trim().toLowerCase() !== account.email;
  const passwordChanged = draft !== null && draft.newPassword.length > 0;
  const needsCurrentPassword = emailChanged || passwordChanged;

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!draft || !account) return;
    const next: Errors = {};
    if (draft.name.trim().length > MAX_NAME_LENGTH) next.name = `Keep your name under ${MAX_NAME_LENGTH} characters.`;
    if (draft.dob) {
      const { error } = validateDateOfBirth(draft.dob);
      if (error) next.dob = error;
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(draft.email.trim())) next.email = "Enter a valid email address.";
    if (passwordChanged && draft.newPassword.length < MIN_PASSWORD_LENGTH) {
      next.newPassword = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    }
    if (needsCurrentPassword && !draft.currentPassword) {
      next.currentPassword = "Enter your current password to change your email or password.";
    }
    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setSaving(true);
    try {
      // Credentials first: if the current password is wrong, nothing else changes either.
      if (needsCurrentPassword) {
        await updateCredentials({
          current_password: draft.currentPassword,
          ...(emailChanged ? { new_email: draft.email.trim() } : {}),
          ...(passwordChanged ? { new_password: draft.newPassword } : {}),
        });
      }
      await updateProfile({
        ...(draft.name.trim() ? { name: draft.name.trim() } : {}),
        ...(draft.dob ? { date_of_birth: draft.dob } : {}),
        default_biological_sex: draft.sex,
        ...(draft.activity ? { default_activity_multiplier: Number(draft.activity) } : {}),
        default_fitness_goal: draft.goal,
      });
      await refresh();
      setMode("view");
      setDraft(null);
      setSavedNote(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setErrors({ currentPassword: "That isn't your current password." });
      } else if (err instanceof ApiError && err.status === 409) {
        setErrors({ email: "Another account already uses this email." });
      } else if (err instanceof ApiError && err.status === 422) {
        setErrors({ form: typeof err.detail === "string" ? err.detail : "Please check your details and try again." });
      } else {
        setErrors({ form: "Couldn't save your changes. Please try again." });
      }
    } finally {
      setSaving(false);
    }
  };

  const leaveEdit = () => {
    if (isDirty) setDialog("discard");
    else {
      setMode("view");
      setDraft(null);
    }
  };

  const handleSignOut = async () => {
    setBusy(true);
    await signOut();
    router.push("/");
  };

  const handleDelete = async () => {
    setBusy(true);
    setDialogError(null);
    try {
      await deleteAccount();
      await signOut().catch(() => {});
      router.push("/");
    } catch (err) {
      setBusy(false);
      setDialogError(err instanceof ApiError ? String(err.message) : "Couldn't delete your account. Please try again.");
    }
  };

  if (!account) {
    return (
      <PhoneFrame bg="bg-[#3e3e3e]">
        <p role="status" className="pt-[200px] text-center text-[12px] text-white/60">
          Loading your profile…
        </p>
      </PhoneFrame>
    );
  }

  return (
    <PhoneFrame bg="bg-[#3e3e3e]" scrollable>
      {mode === "view" || !draft ? (
        <>
          <Header title="Profile" back={<BackButton href="/dashboard" label="Back to dashboard" />} />
          <div className="flex min-h-[754px] flex-col px-[30px] pb-[24px] pt-[31px]">
            {savedNote && (
              <p role="status" className="mb-[12px] rounded-[8px] bg-[#117d69]/30 p-[10px] text-center text-[11px] font-bold text-[#d6f5ef]">
                Your profile has been updated.
              </p>
            )}
            <section className={`${cardClass} p-[20px]`}>
              <dl className="grid grid-cols-2 gap-x-[20px] gap-y-[20px]">
                {(
                  [
                    ["Name", account.name || "—"],
                    ["Biological Sex", account.default_biological_sex === "female" ? "Female" : account.default_biological_sex === "male" ? "Male" : "—"],
                    ["Date of Birth", formatDob(account.date_of_birth)],
                    [
                      "Activity Level",
                      account.default_activity_multiplier != null
                        ? ACTIVITY_LABELS[account.default_activity_multiplier] ?? `${account.default_activity_multiplier}x`
                        : "—",
                    ],
                    ["E-mail", account.email],
                    ["Goals", account.default_fitness_goal ? GOAL_LABELS[account.default_fitness_goal] : "—"],
                    ["Password", "••••••••••"],
                  ] as const
                ).map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-[10px] text-black/70">{label}</dt>
                    <dd className="mt-[5px] break-words text-[14px] font-bold">{value}</dd>
                  </div>
                ))}
              </dl>
              <button type="button" onClick={startEditing} className={`${btn.primary} mt-[30px]`}>
                <Icon name="pencil" size={12} />
                Edit Profile
              </button>
            </section>

            <div className="mt-auto space-y-[15px] pt-[40px]">
              <button type="button" onClick={() => setDialog("signOut")} className={`${btn.light} text-black`}>
                <Icon name="logout" size={20} className="text-[#117d69]" />
                Sign Out
              </button>
              <button
                type="button"
                onClick={() => {
                  setDialogError(null);
                  setDialog("delete");
                }}
                className={`${btn.light} text-rose-700`}
              >
                <Icon name="trash" size={16} />
                Delete Account
              </button>
            </div>
          </div>
        </>
      ) : (
        <>
          <Header
            title="Edit Profile"
            back={
              <button
                type="button"
                onClick={leaveEdit}
                aria-label="Back to profile"
                className="inline-flex h-[28px] w-[75px] items-center justify-center gap-[5px] rounded-[60px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] text-[12px] font-bold tracking-[0.04em] text-black shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#117d69]"
              >
                <Icon name="arrowLeft" size={16} />
                <span aria-hidden="true">back</span>
              </button>
            }
          />
          <div className="px-[30px] pb-[40px] pt-[31px]">
            <form noValidate onSubmit={handleSave} className={`${cardClass} space-y-[15px] p-[30px]`}>
              <TextField
                label="Name"
                icon="person"
                autoComplete="name"
                maxLength={MAX_NAME_LENGTH}
                placeholder="Enter your name"
                value={draft.name}
                error={errors.name}
                onChange={(e) => set("name", e.target.value)}
              />
              <TextField
                label="Date of Birth"
                icon="calendar"
                type="date"
                max={todayIso()}
                value={draft.dob}
                error={errors.dob}
                onChange={(e) => set("dob", e.target.value)}
              />
              <TextField
                label="Email Address"
                icon="email"
                type="email"
                autoComplete="email"
                value={draft.email}
                error={errors.email}
                onChange={(e) => set("email", e.target.value)}
              />
              <PasswordField
                label="New Password"
                autoComplete="new-password"
                placeholder="Leave blank to keep your current one"
                value={draft.newPassword}
                error={errors.newPassword}
                onChange={(e) => set("newPassword", e.target.value)}
              />
              {needsCurrentPassword && (
                <PasswordField
                  label="Current Password"
                  autoComplete="current-password"
                  placeholder="Needed to change email or password"
                  value={draft.currentPassword}
                  error={errors.currentPassword}
                  onChange={(e) => set("currentPassword", e.target.value)}
                />
              )}
              <RadioGroup label="Biological Sex" name="sex" value={draft.sex} onChange={(v) => set("sex", v)} options={SEX_OPTIONS} />
              <SelectField
                label="Activity Level"
                placeholder="Choose your activity level"
                value={draft.activity}
                onChange={(v) => set("activity", v)}
                options={ACTIVITY_OPTIONS}
              />
              <OptionCards label="Goals" name="goal" value={draft.goal} onChange={(v) => set("goal", v)} options={GOAL_OPTIONS} />
              <p className="text-[10px] leading-relaxed text-black/60">
                Changes apply to your next scan. Scans you&apos;ve already saved keep the details
                they were made with.
              </p>
              {errors.form && (
                <p role="alert" className="text-[11px] font-medium text-rose-700">
                  {errors.form}
                </p>
              )}
              <button type="submit" disabled={saving} className={`${btn.primary} !mt-[30px]`}>
                <Icon name="save" size={16} />
                {saving ? "Saving…" : "Save"}
              </button>
            </form>
          </div>
        </>
      )}

      <ConfirmDialog
        open={dialog === "signOut"}
        title="Sign Out?"
        body="Are you sure you want to sign out of your account?"
        confirmLabel="Sign Out"
        destructive={false}
        busy={busy}
        onCancel={() => setDialog(null)}
        onConfirm={handleSignOut}
      />
      <ConfirmDialog
        open={dialog === "delete"}
        title="Delete Account?"
        body={`This permanently deletes your account (${account.email}) and every saved report and result. It can't be undone, and nothing is kept.`}
        confirmLabel="Delete Account"
        confirmIcon="trash"
        busy={busy}
        error={dialogError}
        onCancel={() => setDialog(null)}
        onConfirm={handleDelete}
      />
      <ConfirmDialog
        open={dialog === "discard"}
        title="Discard Changes?"
        body="Are you sure you want to discard your profile changes? Any unsaved changes will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep Editing"
        confirmIcon="trash"
        onCancel={() => setDialog(null)}
        onConfirm={() => {
          setDialog(null);
          setDraft(null);
          setMode("view");
        }}
      />
    </PhoneFrame>
  );
}
