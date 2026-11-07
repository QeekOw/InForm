import { normalizeFieldKey } from "./corrections";
import type { SampleExtraction } from "./inbody";

export type PlanReviewError = {
  message: string;
  unread: string[];
  flagged: string[];
};

export function parsePlanReviewError(detail: unknown, status: number): PlanReviewError {
  let message = `API returned ${status}`;
  if (typeof detail === "string") message = detail;
  else if (Array.isArray(detail)) {
    message = detail.map((item: unknown) => {
      if (!item || typeof item !== "object") return "value: invalid";
      const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.at(-1) : "value";
      const msg = "msg" in item && typeof item.msg === "string" ? item.msg : "invalid";
      return `${loc ?? "value"}: ${msg}`;
    }).join("\n");
  }
  else if (detail && typeof detail === "object" && "message" in detail) message = String(detail.message);
  const unread = detail && typeof detail === "object" && "unread" in detail ? detail.unread : [];
  const flagged = detail && typeof detail === "object" && "flagged" in detail ? detail.flagged : [];
  return {
    message,
    unread: Array.isArray(unread) ? unread.filter((key): key is string => typeof key === "string") : [],
    flagged: Array.isArray(flagged) ? flagged.filter((key): key is string => typeof key === "string") : [],
  };
}

export function mergeReviewRequirements(extraction: SampleExtraction, review: PlanReviewError): SampleExtraction {
  return {
    ...extraction,
    unread: [...new Set([...extraction.unread, ...review.unread].map(normalizeFieldKey))],
    flagged: [...new Set([...extraction.flagged, ...review.flagged].map(normalizeFieldKey))],
  };
}
