"use client";

import { useEffect, useState, Suspense, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import BackButton from "@/components/BackButton";
import Icon from "@/components/Icon";
import PhoneFrame from "@/components/PhoneFrame";
import {
  btn,
  Card,
  OptionCards,
  PasswordField,
  PhotoBackdrop,
  RadioGroup,
  SelectField,
  TextField,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { ACTIVITY_OPTIONS, GOAL_OPTIONS, SEX_OPTIONS } from "@/lib/profileOptions";
import { loadJSON, removeSessionItem, SESSION_KEYS } from "@/lib/session";
import {
  todayIso,
  validateDateOfBirth,
  type BiologicalSex,
  type FitnessGoal,
  type UserProfile,
} from "@/lib/user";

// Mirrors backend/main.py's SignupRequest validation.
const MIN_PASSWORD_LENGTH = 8;
const MAX_NAME_LENGTH = 80;

type Errors = Partial<
  Record<"email" | "password" | "confirmPassword" | "name" | "dob" | "activity", string>
>;

function SignUpContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");
  const { signUp } = useAuth();

  // Two screens, one request: credentials first, then "About You". Nothing is
  // sent until the second screen is submitted, so nothing is asked twice.
  const [step, setStep] = useState<"account" | "about">("account");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState<BiologicalSex>("male");
  const [activity, setActivity] = useState("");
  const [goal, setGoal] = useState<FitnessGoal>("fat_loss");

  const [errors, setErrors] = useState<Errors>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // A guest who already finished a plan shouldn't retype what they told us.
  useEffect(() => {
    const guestProfile = loadJSON<UserProfile>(SESSION_KEYS.profile);
    // sessionStorage is a browser-only external store, unreadable during SSR.
    /* eslint-disable react-hooks/set-state-in-effect */
    if (guestProfile) {
      setSex(guestProfile.biological_sex);
      setActivity(String(guestProfile.activity_multiplier));
      setGoal(guestProfile.fitness_goal);
    }
    const guestName = loadJSON<string>(SESSION_KEYS.name);
    if (guestName) setName(guestName);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const clear = (field: keyof Errors) => setErrors((p) => ({ ...p, [field]: undefined }));

  const handleNext = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: Errors = {};
    if (!email.trim()) next.email = "Email address can't be empty.";
    else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) next.email = "Enter a valid email address.";
    if (!password) next.password = "Password can't be empty.";
    else if (password.length < MIN_PASSWORD_LENGTH) {
      next.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    }
    if (confirmPassword !== password) next.confirmPassword = "Passwords don't match.";
    setErrors(next);
    setNotice(null);
    if (Object.keys(next).length === 0) setStep("about");
  };

  const handleSignUp = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: Errors = {};
    if (name.trim().length > MAX_NAME_LENGTH) next.name = `Keep your name under ${MAX_NAME_LENGTH} characters.`;
    const dobCheck = validateDateOfBirth(dob);
    if (dobCheck.error) next.dob = dobCheck.error;
    if (!activity) next.activity = "Choose your activity level.";
    setErrors(next);
    setNotice(null);
    if (Object.keys(next).length > 0) return;

    setSubmitting(true);
    try {
      await signUp({
        email,
        password,
        name: name.trim() || null,
        date_of_birth: dob,
        default_biological_sex: sex,
        default_activity_multiplier: Number(activity),
        default_fitness_goal: goal,
      });
      const target = redirectParam || loadJSON<string>(SESSION_KEYS.nextAfterAuth) || "/dashboard";
      removeSessionItem(SESSION_KEYS.nextAfterAuth);
      router.push(target);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // The email lives on the first screen, so send them back to fix it.
        setStep("account");
        setErrors({ email: "An account with this email already exists. Try logging in instead." });
      } else if (err instanceof ApiError && err.status === 422) {
        setNotice(typeof err.detail === "string" ? err.detail : "Please check your details and try again.");
      } else {
        setNotice("Something went wrong creating your account. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const signInHref = redirectParam
    ? `/sign-in?redirect=${encodeURIComponent(redirectParam)}`
    : "/sign-in";
  const isSavingScan = redirectParam?.includes("/result") ?? false;

  return (
    <PhoneFrame bg="bg-[#3e3e3e]" scrollable>
      <PhotoBackdrop src="/bg/signup.jpg" className="absolute inset-0 min-h-full" />

      <div className="relative px-[30px] pb-[40px] pt-[48px]">
        {step === "account" ? (
          <BackButton href={signInHref} />
        ) : (
          <button
            type="button"
            onClick={() => setStep("account")}
            aria-label="Back to account details"
            className="inline-flex h-[28px] w-[75px] items-center justify-center gap-[5px] rounded-[60px] bg-gradient-to-b from-[#fcfcfc] to-[#f3f3f3] text-[12px] font-bold tracking-[0.04em] text-black shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#117d69]"
          >
            <Icon name="arrowLeft" size={16} />
            <span aria-hidden="true">back</span>
          </button>
        )}

        <h1 className="mt-[72px] text-center text-[40px] font-bold tracking-[0.02em] text-[#fcfcfc]">
          {step === "account" ? "Sign Up" : "About You"}
        </h1>
        {isSavingScan && step === "account" && (
          <p className="mt-1 text-center text-[12px] font-medium text-[#7ee0cf]">
            Create an account to save your scan and track your progress
          </p>
        )}
        <p className="sr-only" aria-live="polite">
          Step {step === "account" ? 1 : 2} of 2
        </p>

        <Card className="mt-[36px] p-[30px]">
          {step === "account" ? (
            <form noValidate onSubmit={handleNext} className="space-y-[15px]">
              <TextField
                label="Email Address"
                icon="email"
                type="email"
                autoComplete="email"
                placeholder="Enter your email address"
                value={email}
                error={errors.email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  clear("email");
                }}
              />
              <PasswordField
                label="Password"
                autoComplete="new-password"
                placeholder="Create a password"
                value={password}
                error={errors.password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  clear("password");
                }}
              />
              <PasswordField
                label="Confirm Password"
                autoComplete="new-password"
                placeholder="Confirm your password"
                value={confirmPassword}
                error={errors.confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  clear("confirmPassword");
                }}
              />
              <button type="submit" className={`${btn.primary} !mt-[40px]`}>
                Next
              </button>
            </form>
          ) : (
            <form noValidate onSubmit={handleSignUp} className="space-y-[15px]">
              <TextField
                label="Name"
                icon="person"
                autoComplete="name"
                placeholder="Enter your name"
                maxLength={MAX_NAME_LENGTH}
                value={name}
                error={errors.name}
                onChange={(e) => {
                  setName(e.target.value);
                  clear("name");
                }}
              />
              <TextField
                label="Date of Birth"
                icon="calendar"
                type="date"
                max={todayIso()}
                value={dob}
                error={errors.dob}
                onChange={(e) => {
                  setDob(e.target.value);
                  clear("dob");
                }}
              />
              <RadioGroup label="Biological Sex" name="sex" value={sex} onChange={setSex} options={SEX_OPTIONS} />
              <SelectField
                label="Activity Level"
                placeholder="Choose your activity level"
                value={activity}
                error={errors.activity}
                onChange={(v) => {
                  setActivity(v);
                  clear("activity");
                }}
                options={ACTIVITY_OPTIONS}
              />
              <OptionCards label="Goals" name="goal" value={goal} onChange={setGoal} options={GOAL_OPTIONS} />
              <p className="text-[10px] leading-relaxed text-black/60">
                Used to work out your calorie target and pick your exercises. Saved so your next
                scan starts filled in.
              </p>
              <button type="submit" disabled={submitting} className={`${btn.primary} !mt-[30px]`}>
                {submitting ? "Creating account…" : "Sign Up"}
              </button>
            </form>
          )}

          {notice && (
            <p
              role="status"
              className="mt-3 rounded-[8px] bg-[#117d69]/10 px-3 py-2 text-center text-[11px] text-[#0b5c4d]"
            >
              {notice}
            </p>
          )}
        </Card>

        {step === "account" && (
          <p className="mt-[26px] text-center text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]">
            already have an account?{" "}
            <Link href={signInHref} className="underline">
              Log In
            </Link>
          </p>
        )}
      </div>
    </PhoneFrame>
  );
}

export default function SignUp() {
  return (
    <Suspense
      fallback={
        <PhoneFrame bg="bg-[#3e3e3e]">
          <div className="flex h-full items-center justify-center text-[14px] text-white">
            Loading…
          </div>
        </PhoneFrame>
      }
    >
      <SignUpContent />
    </Suspense>
  );
}
