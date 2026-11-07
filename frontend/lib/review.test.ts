import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import SavedBalance from "@/components/SavedBalance";
import { DEFAULT_READING, type SampleExtraction } from "./inbody";
import { mergeReviewRequirements, parsePlanReviewError } from "./planReview";

it("does not reassure a person whose saved balance was unassessed", () => {
  const html = renderToStaticMarkup(createElement(SavedBalance, {
    plan: { detected_imbalances: [], unconfirmed_imbalance_pairs: ["arm", "leg"] },
  }));
  expect(html).toContain("not assessed");
  expect(html).toContain("arm and leg");
  expect(html).not.toContain("within 5%");
});

it("names unassessed pairs alongside detected imbalances", () => {
  const html = renderToStaticMarkup(createElement(SavedBalance, {
    plan: { detected_imbalances: ["left_arm"], unconfirmed_imbalance_pairs: ["leg"] },
  }));
  expect(html).toContain("left_arm");
  expect(html).toContain("not assessed");
  expect(html).toContain("leg");
});

it("reassures only when both pairs were assessed with no imbalance", () => {
  const html = renderToStaticMarkup(createElement(SavedBalance, {
    plan: { detected_imbalances: [], unconfirmed_imbalance_pairs: [] },
  }));
  expect(html).toContain("within 5%");
  expect(html).not.toContain("not assessed");
});

it("treats missing legacy assessment metadata as unknown", () => {
  const html = renderToStaticMarkup(createElement(SavedBalance, { plan: { detected_imbalances: [] } }));
  expect(html).toContain("not assessed");
  expect(html).not.toContain("within 5%");
});

it("preserves exact unresolved values from plan rejection", () => {
  expect(parsePlanReviewError({ message: "Review required", unread: ["weight_kg"], flagged: ["segmental_lean.left_arm_kg"] }, 409))
    .toEqual({ message: "Review required", unread: ["weight_kg"], flagged: ["segmental_lean.left_arm_kg"] });
});

it("does not accept malformed field lists from an error response", () => {
  expect(parsePlanReviewError({ message: "Bad request", unread: "weight_kg", flagged: [null, 1] }, 422))
    .toEqual({ message: "Bad request", unread: [], flagged: [] });
});

it("hands new backend requirements to review without changing measured values", () => {
  const extraction: SampleExtraction = {
    status: "complete", data: DEFAULT_READING, unread: ["weight_kg"], flagged: ["lean_body_mass_kg"],
  };
  const merged = mergeReviewRequirements(extraction, {
    message: "Review required", unread: ["weight_kg"], flagged: ["segmental_lean.left_arm_kg"],
  });
  expect(merged.data).toBe(extraction.data);
  expect(merged.unread).toEqual(["weight_kg"]);
  expect(merged.flagged).toEqual(["lean_body_mass_kg", "segmental_lean.left_arm_kg"]);
  expect(extraction.flagged).toEqual(["lean_body_mass_kg"]);
});
