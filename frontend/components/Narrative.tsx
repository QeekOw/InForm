// The written plan, and where it came from.
//
// The provenance label is the point of this component existing: a reader has to
// be able to tell prose an AI wrote from a deterministic summary of the same
// numbers (issue #36, issue #29 stories 50-52). The numbers themselves are never
// generated either way — they come out of the pipeline's fixed formulas — and the
// note says so, so the label can't be mistaken for a claim about the figures.

export type NarrativeSource = "generated" | "fallback";

export const NARRATIVE_SOURCES: Record<NarrativeSource, { label: string; note: string }> = {
  generated: {
    label: "Written plan",
    note: "Written by AI around your computed figures. The figures themselves are computed, not generated.",
  },
  fallback: {
    label: "Summary",
    note: "No AI wrote this one. It's a plain summary of the same computed figures, assembled from a fixed template.",
  },
};

/** The narrative's own text, rendered as plain lines.
 *
 * It may carry light markdown — the fallback plan always does — so asterisks and
 * hashes are turned into emphasis and headings rather than shown raw. */
export function NarrativeText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => {
        const plain = line.replace(/\*\*/g, "").trim();
        if (!plain) return null;
        const heading = plain.match(/^#+\s*(.*)$/);
        return heading ? (
          <p key={i} className="pt-2 font-bold first:pt-0">
            {heading[1]}
          </p>
        ) : (
          <p key={i}>{plain}</p>
        );
      })}
    </>
  );
}

/** The label and its explanatory note, for wherever a narrative is shown. */
export function NarrativeProvenance({
  source,
  className = "",
}: {
  source: NarrativeSource;
  className?: string;
}) {
  const { label, note } = NARRATIVE_SOURCES[source];
  return (
    <div className={className}>
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#2dd4bf]">{label}</p>
      <p className="mt-1 text-[10px] leading-relaxed text-white/60">{note}</p>
    </div>
  );
}
