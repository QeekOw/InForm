"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import BackButton from "@/components/BackButton";
import PhoneFrame from "@/components/PhoneFrame";
import { btn, Card, OptionCards, PhotoBackdrop, RadioGroup, SelectField, TextField } from "@/components/ui";
import { ACTIVITY_OPTIONS, GOAL_OPTIONS, SEX_OPTIONS } from "@/lib/profileOptions";
import { useAuth } from "@/lib/AuthProvider";
import { isFinishingGuestPlan, nextAfterProfile } from "@/lib/flow";
import { getCurrentScan } from "@/lib/scans";
import { clearSheet, saveJSON, SESSION_KEYS } from "@/lib/session";
import {
  ACTIVITY_LEVELS,
  DEFAULT_USER_NAME,
  todayIso,
  validateDateOfBirth,
  type UserProfile,
} from "@/lib/user";


/** Where the form's starting values came from, so the screen can say so rather
 * than silently presenting numbers the person didn't type this time. */
type PrefillSource = "none" | "account" | "last-scan";

const DEFAULT_ACTIVITY_MULTIPLIER = ACTIVITY_LEVELS[2].multiplier;

export default function Profile() {
  const router = useRouter();
  const { account } = useAuth();
  const [finishingGuestPlan, setFinishingGuestPlan] = useState(false);
  const [name, setName] = useState("");
  const [ageError, setAgeError] = useState<string | null>(null);

  // The most recent Scan's frozen profile snapshot, read *only* to pre-fill this
  // form. Never written back: editing anything here cannot change that Scan
  // (issue #42).
  const [lastScanProfile, setLastScanProfile] = useState<UserProfile | null>(null);

  // What the person has typed or picked this visit. `null` means "untouched, use
  // whatever we know about them" â€” so the form's values are *derived* from the
  // account rather than copied into state when it loads, which would mean
  // reacting to our own data as though it were an external system.
  const [dobEdit, setDobEdit] = useState<string | null>(null);
  const [sexEdit, setSexEdit] = useState<UserProfile["biological_sex"] | null>(null);
  const [activityEdit, setActivityEdit] = useState<number | null>(null);
  const [goalEdit, setGoalEdit] = useState<UserProfile["fitness_goal"] | null>(null);

  useEffect(() => {
    // sessionStorage is a browser-only external store, unreadable during SSR.
    const isFinishing = isFinishingGuestPlan();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFinishingGuestPlan(isFinishing);
    if (!account && !isFinishing) {
      clearSheet();
    }
  }, [account]);

  // If an authenticated user already completed profile defaults, do not prompt again.
  useEffect(() => {
    if (
      account &&
      account.date_of_birth &&
      account.default_biological_sex &&
      account.default_activity_multiplier &&
      account.default_fitness_goal
    ) {
      const { age, error } = validateDateOfBirth(account.date_of_birth);
      if (error === null && age !== null) {
        const profile: UserProfile = {
          age,
          biological_sex: account.default_biological_sex,
          activity_multiplier: account.default_activity_multiplier,
          fitness_goal: account.default_fitness_goal,
        };
        saveJSON(SESSION_KEYS.profile, profile);
        saveJSON(SESSION_KEYS.name, account.name || account.email.split("@")[0] || DEFAULT_USER_NAME);
        router.replace(nextAfterProfile());
      }
    }
  }, [account, router]);

  // A signed-in person shouldn't retype what they already told us
  // (Requirement 3.8). Two sources, preferred in this order:
  //
  //   1. The Account's own defaults, given at sign-up. The person's current
  //      answers, and the only source that can supply a date of birth.
  //   2. Failing that, the most recent Scan's frozen profile.
  //
  // A guest has neither and gets the form's plain defaults, so the anonymous
  // flow is untouched (Requirement 3.9).
  const hasAccountDefaults = Boolean(
    account &&
      (account.default_biological_sex !== null ||
        account.default_activity_multiplier !== null ||
        account.default_fitness_goal !== null ||
        account.date_of_birth !== null),
  );

  // Only worth asking for a Scan when the account has no defaults of its own.
  useEffect(() => {
    if (!account || hasAccountDefaults) return;
    let active = true;
    getCurrentScan()
      .then((plan) => {
        if (active) setLastScanProfile(plan.profile);
      })
      .catch(() => {
        // No previous Scan (or not reachable): keep the form's defaults.
      });
    return () => {
      active = false;
    };
  }, [account, hasAccountDefaults]);

  const prefillSource: PrefillSource = hasAccountDefaults
    ? "account"
    : lastScanProfile
      ? "last-scan"
      : "none";

  // A Scan freezes the age it was taken at, never a birth date, so only an
  // account default can pre-fill this. Working a birth date back from an age
  // would be inventing a value the person never gave.
  const dob = dobEdit ?? account?.date_of_birth ?? "";
  const sex =
    sexEdit ?? account?.default_biological_sex ?? lastScanProfile?.biological_sex ?? "male";
  const activityMultiplier =
    activityEdit ??
    account?.default_activity_multiplier ??
    lastScanProfile?.activity_multiplier ??
    DEFAULT_ACTIVITY_MULTIPLIER;
  const goal =
    goalEdit ?? account?.default_fitness_goal ?? lastScanProfile?.fitness_goal ?? "fat_loss";

  const handleContinue = () => {
    const { age, error } = validateDateOfBirth(dob);
    if (error !== null) {
      setAgeError(error);
      return;
    }

    const profile: UserProfile = {
      age,
      biological_sex: sex,
      activity_multiplier: activityMultiplier,
      fitness_goal: goal,
    };
    saveJSON(SESSION_KEYS.profile, profile);
    saveJSON(SESSION_KEYS.name, name || DEFAULT_USER_NAME);
    router.push(nextAfterProfile());
  };

  return (
    <PhoneFrame bg="bg-[#3e3e3e]" scrollable>
      <PhotoBackdrop src="/bg/signup.jpg" className="absolute inset-0 min-h-full" />

      <div className="relative px-[30px] pb-[40px] pt-[48px]">
        {/* Reached from the gallery, sign-in and a guest's results, so it walks
            the in-app trail instead of guessing. */}
        <BackButton fallbackHref="/upload" />

        <h1 className="mt-[72px] text-center text-[40px] font-bold tracking-[0.02em] text-[#fcfcfc]">
          About You
        </h1>
        {(finishingGuestPlan || prefillSource !== "none") && (
          <p className="mt-1 text-center text-[12px] text-[#fcfcfc]/90">
            {finishingGuestPlan
              ? "Your plan needs these details. Fill them in to see it."
              : prefillSource === "account"
                ? "Filled in from your account. Change anything that's moved on."
                : "Pre-filled from your last scan. Please re-enter your date of birth."}
          </p>
        )}

        <Card as="form" className="mt-[36px] space-y-[15px] p-[30px]">
          <TextField
            label="Name"
            icon="person"
            autoComplete="name"
            placeholder="Enter your name (optional)"
            maxLength={80}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <TextField
            label="Date of Birth"
            icon="calendar"
            type="date"
            max={todayIso()}
            value={dob}
            error={ageError}
            onChange={(e) => {
              setDobEdit(e.target.value);
              setAgeError(null);
            }}
          />
          <RadioGroup label="Biological Sex" name="sex" value={sex} onChange={setSexEdit} options={SEX_OPTIONS} />
          <SelectField
            label="Activity Level"
            value={String(activityMultiplier)}
            onChange={(v) => setActivityEdit(Number(v))}
            options={ACTIVITY_OPTIONS}
          />
          <OptionCards label="Goals" name="goal" value={goal} onChange={setGoalEdit} options={GOAL_OPTIONS} />
          <button
            type="submit"
            className={`${btn.primary} !mt-[30px]`}
            onClick={(e) => {
              e.preventDefault();
              handleContinue();
            }}
          >
            Continue
          </button>
        </Card>
      </div>
    </PhoneFrame>
  );
}
