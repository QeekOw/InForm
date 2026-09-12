"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import PhoneFrame from "@/components/PhoneFrame";
import { saveJSON } from "@/lib/session";
import { SESSION_KEYS, type UserProfile } from "@/lib/inbody";

const imgRadioSelected = "/icons/form/radio-selected.svg";
const imgRadioUnselected = "/icons/form/radio-unselected.svg";

const ACTIVITY_LEVELS = [
  { label: "Sedentary", multiplier: 1.2 },
  { label: "Lightly active", multiplier: 1.375 },
  { label: "Moderately active", multiplier: 1.55 },
  { label: "Very active", multiplier: 1.725 },
  { label: "Extremely active", multiplier: 1.9 },
];

function ageFromDob(dob: string): number {
  if (!dob) return 30;
  const birth = new Date(dob);
  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const hasHadBirthdayThisYear =
    now.getMonth() > birth.getMonth() ||
    (now.getMonth() === birth.getMonth() && now.getDate() >= birth.getDate());
  if (!hasHadBirthdayThisYear) age -= 1;
  return age;
}

export default function Profile() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState<UserProfile["biological_sex"]>("male");
  const [activityMultiplier, setActivityMultiplier] = useState(ACTIVITY_LEVELS[2].multiplier);
  const [goal, setGoal] = useState<UserProfile["fitness_goal"]>("fat_loss");

  const handleContinue = () => {
    const profile: UserProfile = {
      age: ageFromDob(dob),
      biological_sex: sex,
      activity_multiplier: activityMultiplier,
      fitness_goal: goal,
    };
    saveJSON(SESSION_KEYS.profile, profile);
    saveJSON(SESSION_KEYS.name, name || "John Doe");
    router.push("/upload");
  };

  return (
    <PhoneFrame bg="bg-[#3e3e3e]">
      <h1 className="mt-[57px] text-center text-[32px] font-bold tracking-[0.02em] text-[#fcfcfc]">
        Sign Up
      </h1>

      <div className="mx-auto mt-8 w-[342px] rounded-[15px] bg-[#fcfcfc] p-[30px]">
        <label className="block text-[12px] text-black" htmlFor="name">
          Name
        </label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-[9px] h-[35px] w-full rounded-lg border border-[#d9d9d9] bg-[#d9d9d980] px-3 text-[13px]"
        />

        <label className="mt-6 block text-[12px] text-black" htmlFor="dob">
          Date of Birth
        </label>
        <input
          id="dob"
          type="date"
          value={dob}
          onChange={(e) => setDob(e.target.value)}
          className="mt-[9px] h-[35px] w-full rounded-lg border border-[#d9d9d9] bg-[#d9d9d980] px-3 text-[13px]"
        />

        <p className="mt-6 text-[12px] text-black">Biological Sex</p>
        <div className="mt-[9px] flex gap-[42px]">
          {(["male", "female"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setSex(value)}
              className="flex items-center gap-2 text-[12px] font-bold text-black capitalize"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                alt=""
                className="size-4"
                src={sex === value ? imgRadioSelected : imgRadioUnselected}
              />
              {value}
            </button>
          ))}
        </div>

        <label className="mt-6 block text-[12px] text-black" htmlFor="activity">
          Activity Level
        </label>
        <select
          id="activity"
          value={activityMultiplier}
          onChange={(e) => setActivityMultiplier(Number(e.target.value))}
          className="mt-[9px] h-[35px] w-full rounded-lg border border-[#d9d9d9] bg-[#d9d9d980] px-3 text-[13px]"
        >
          {ACTIVITY_LEVELS.map((level) => (
            <option key={level.multiplier} value={level.multiplier}>
              {level.label}
            </option>
          ))}
        </select>

        <p className="mt-6 text-[12px] text-black">Goals</p>
        <div className="mt-[9px] flex flex-col gap-[8px]">
          {(
            [
              { value: "fat_loss", label: "Fat Loss" },
              { value: "hypertrophy", label: "Build Muscle" },
            ] as const
          ).map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setGoal(option.value)}
              className={`h-[35px] rounded-lg border px-4 text-left text-[12px] font-bold ${
                goal === option.value
                  ? "border-[#117d69] bg-[#117d6926] text-[#117d69]"
                  : "border-[#d9d9d9] bg-[#d9d9d980] text-black"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 flex justify-center px-[30px]">
        <button
          type="button"
          onClick={handleContinue}
          className="flex h-[40px] w-full items-center justify-center rounded-lg bg-[#117d69] text-[14px] font-bold tracking-[0.02em] text-[#fcfcfc]"
        >
          Continue
        </button>
      </div>
    </PhoneFrame>
  );
}
