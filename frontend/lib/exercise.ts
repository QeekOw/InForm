// Mirrors inform.exercise.Exercise / ExercisePlan (src/inform/exercise.py).

export type MovementType =
  | "corrective_unilateral"
  | "bilateral_compound"
  | "cardio_hiit";

export type Exercise = {
  name: string;
  target: string;
  body_part: string;
  equipment: string;
  secondary_muscles: string[];
  movement_type: MovementType;
};

export type ExercisePlan = {
  exercises: Exercise[];
  detected_imbalances: string[];
  unconfirmed_imbalance_pairs: ("arm" | "leg")[];
};
