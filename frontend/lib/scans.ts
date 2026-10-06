// Mirrors backend/main.py's Scan-related endpoints (issue #42). Every call
// here requires a signed-in Account (401 otherwise) via the session cookie.

import { apiGet, apiPost } from "./api";
import type { ExercisePlan } from "./exercise";
import type { InBodyPayload, PartialInBody } from "./inbody";
import type { UserProfile } from "./user";

export type NutritionTargets = {
  bmr_kcal: number;
  tdee_kcal: number;
  target_calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fats_g: number;
  fiber_g: number;
};

// Same reading-source shape /plan accepts (sample_id | read_id | measured |
// inbody, exactly one), plus corrections/confirmations — saving a Scan
// freezes exactly what /plan would otherwise just return.
export type SaveScanRequest = {
  user: UserProfile;
  sample_id?: string;
  read_id?: string;
  measured?: PartialInBody;
  inbody?: InBodyPayload;
  corrections?: Record<string, unknown>;
  confirmations?: string[];
  initial_flagged?: string[];
};

// Mirrors backend/main.py's ScanSummary. One dated row per Scan, carrying
// enough to plot the Dashboard's trends and label a history entry, with every
// value read from that Scan's own frozen snapshot rather than recomputed.
export type ScanSummary = {
  id: string;
  created_at: string;
  target_calories_kcal: number;
  weight_kg: number;
  percent_body_fat: number;
  lean_body_mass_kg: number;
  skeletal_muscle_mass_kg: number;
  bmr_kcal: number;
  has_corrections: boolean;
  sample_id?: string | null;
  scan_fingerprint?: string | null;
};

export type ScanDetail = {
  id: string;
  created_at: string;
  source_device: string | null;
  sample_id: string | null;
  profile: UserProfile;
  measured: PartialInBody;
  effective_inbody: InBodyPayload;
  corrected_fields: string[];
  confirmed_fields: string[];
  nutrition: NutritionTargets;
  exercises: ExercisePlan;
  narrative_text: string;
  narrative_source: "generated" | "fallback";
  scan_fingerprint?: string | null;
};

export function computeScanFingerprint(params: {
  sampleId?: string | null;
  weight_kg?: number | null;
  skeletal_muscle_mass_kg?: number | null;
  percent_body_fat?: number | null;
  lean_body_mass_kg?: number | null;
  source_device?: string | null;
}): string {
  const weight = Number(params.weight_kg ?? 0).toFixed(1);
  const smm = Number(params.skeletal_muscle_mass_kg ?? 0).toFixed(1);
  const pbf = Number(params.percent_body_fat ?? 0).toFixed(1);
  const lbm = Number(params.lean_body_mass_kg ?? 0).toFixed(1);
  const source = params.sampleId || params.source_device || "inbody";
  return `${source}|${weight}|${smm}|${pbf}|${lbm}`;
}

export function saveScan(request: SaveScanRequest): Promise<ScanDetail> {
  return apiPost<ScanDetail>("/scans", request);
}

export function listScans(): Promise<ScanSummary[]> {
  return apiGet<ScanSummary[]>("/scans");
}

export function getScan(id: string): Promise<ScanDetail> {
  return apiGet<ScanDetail>(`/scans/${id}`);
}

export type CurrentPlanResponse = ScanDetail & {
  age_days: number;
  is_stale: boolean;
};

export function getCurrentScan(): Promise<CurrentPlanResponse> {
  return apiGet<CurrentPlanResponse>("/scans/current");
}
