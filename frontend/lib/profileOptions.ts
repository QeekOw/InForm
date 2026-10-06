// Option lists shared by every form that collects profile values (sign-up,
// guest profile, edit profile), so the wording stays identical across them.

import type { IconName } from "@/components/Icon";
import { ACTIVITY_LEVELS, type BiologicalSex, type FitnessGoal } from "./user";

export const SEX_OPTIONS: { value: BiologicalSex; label: string }[] = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
];

export const GOAL_OPTIONS: { value: FitnessGoal; label: string; icon: IconName }[] = [
  { value: "fat_loss", label: "Fat Loss", icon: "scale" },
  { value: "hypertrophy", label: "Build Muscle", icon: "dumbbell" },
];

export const GOAL_LABELS: Record<FitnessGoal, string> = {
  fat_loss: "Fat Loss",
  hypertrophy: "Build Muscle",
};

export const ACTIVITY_OPTIONS = ACTIVITY_LEVELS.map((l) => ({
  value: String(l.multiplier),
  label: `${l.label} (${l.hint})`,
}));
