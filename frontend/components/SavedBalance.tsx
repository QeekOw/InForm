import type { ExercisePlan } from "@/lib/exercise";

export default function SavedBalance({ plan }: {
  plan: Pick<ExercisePlan, "detected_imbalances"> & Partial<Pick<ExercisePlan, "unconfirmed_imbalance_pairs">>;
}) {
  const unassessed = plan.unconfirmed_imbalance_pairs ?? ["arm", "leg"];
  return (
    <>
      {plan.detected_imbalances.length === 0 && unassessed.length === 0 && (
        <p className="mt-[8px] text-[11px] text-[#0b5e4f]">
          Your left and right sides were within 5% of each other at this scan.
        </p>
      )}
      {plan.detected_imbalances.length > 0 && (
        <ul className="mt-[8px] list-disc pl-4 text-[11px]">
          {plan.detected_imbalances.map((imbalance) => <li key={imbalance}>{imbalance}</li>)}
        </ul>
      )}
      {unassessed.length > 0 && (
        <p className="mt-[8px] text-[11px] text-amber-800">
          Balance was not assessed for your {unassessed.join(" and ")} because those readings were not confirmed.
        </p>
      )}
    </>
  );
}
