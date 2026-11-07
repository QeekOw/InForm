import type { ExercisePlan } from "@/lib/exercise";

export default function SavedBalance({ plan }: {
  plan: Pick<ExercisePlan, "detected_imbalances"> & Partial<Pick<ExercisePlan, "unconfirmed_imbalance_pairs">>;
}) {
  return plan.detected_imbalances.length === 0 ? (
    <p className="mt-[8px] text-[11px] text-[#0b5e4f]">
      Your left and right sides were within 5% of each other at this scan.
    </p>
  ) : (
    <ul className="mt-[8px] list-disc pl-4 text-[11px]">
      {plan.detected_imbalances.map((imbalance) => <li key={imbalance}>{imbalance}</li>)}
    </ul>
  );
}
