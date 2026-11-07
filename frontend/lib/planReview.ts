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
  return { message, unread: [], flagged: [] };
}
import type { SampleExtraction } from "./inbody";


export function mergeReviewRequirements(extraction: SampleExtraction, _review: PlanReviewError): SampleExtraction {
  return extraction;
}
