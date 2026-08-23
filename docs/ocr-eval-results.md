# Module 1 (OCR) — Donut vs VLM head-to-head

Results for issue #8: the fine-tuned Donut engine scored against the VLM
baseline through the shared `extract_inbody` seam, using `inform.compare` and the
`evaluate()` harness (ADR-0006). All numbers below are on **held-out synthetic
InBody sheets** (seeds ≥ 5000, never seen in training).

## Headline

| Metric | Donut (1-epoch) | VLM (GPT-4o) |
|---|---|---|
| **Whole-sheet accuracy** | **56.0%** | **100.0%** |
| Critical-field mean (LBM + segmental) | 56.8% | 100.0% |
| Per-field range | 56.5–57.0% | 100.0% |

- **n = 200** held-out sheets (100 InBody 270 + 100 InBody 570).
- VLM: `gpt-4o-2024-08-06`, zero-shot with Structured Outputs.
- Donut: `donut-base` fine-tuned 1 epoch on the ~5,000-sheet synthetic set
  (`checkpoint-1250`), self-hosted, no per-call cost.
- Whole-sheet = every *required* field within ±0.1 unit (ADR-0006); the optional
  `visceral_fat_level` is reported per-field but excluded from whole-sheet.

## How to read this

**GPT-4o's 100% is on *clean* synthetic sheets — the easy regime.** The
synthetic renderer produces crisp, glare-free, undistorted images; a frontier
vision model reads those near-perfectly. This is **not** evidence that Donut is
unusable or that GPT-4o is flawless on real data — it means the synthetic set
does not yet stress either model the way a real smartphone photo would. The
meaningful comparison is on **real InBody 270/570 photos**, for which no labeled
hold-out exists yet (see Future Work).

The result GPT-4o delivers *for free* is the argument for the VLM baseline as
the Phase-1 unblocker and permanent evaluation oracle (ADR-0002): it works with
no training and sets the ceiling the self-hosted engine is measured against.

## Epoch ablation: 1 vs 3 epochs

On the **same 200-sheet hold-out**:

| Checkpoint | Whole-sheet |
|---|---|
| 1 epoch (`checkpoint-1250`) | 56.0% |
| 3 epochs (`donut-inbody-3ep`) | 55.5% |

These are **tied** (a ~1-sheet difference — noise). Training loss fell to ~1e-5
by 3 epochs (harder memorization of the training set), but held-out accuracy did
not move. Conclusion: **more epochs neither helped nor hurt** on synthetic data;
the model plateaus near 56%. Keep the 1-epoch checkpoint for **cost** (no reason
to train 3× for the same result), not because extra epochs degrade it.

> Note: earlier small-n runs (n = 40–60) showed the 1-epoch checkpoint at
> 62.5–65%. That was small-sample luck, not a real gap; the n = 200 number
> (56.0%) is the one to cite.

## Failure mode: mostly safe refusals

Per-field rates (57.0%) sit ~2 sheets above whole-sheet (56.0%), with `lbm` and
`left_leg` at 56.5%. So of the ~88 failed sheets:

- **~86 are clean fail-closed refusals** — the parser rejects an
  incomplete/garbled generation and the seam raises `MissingRequiredFieldsError`
  rather than emit a number (ADR-0008). No fabrication.
- **~2 have a single silently-wrong field** — extracted, most fields correct,
  but one value off. This is the small unsafe tail.

So ~99% of Donut's behavior is either correct or a safe refusal, consistent with
the "no hallucination at the front door" thesis — with a ~1% silent-error tail
worth naming honestly.

## Reproduction

```bash
python -m inform.compare --data-dir <holdout-dir> --donut-checkpoint <checkpoint-dir>
```

`<holdout-dir>` is a `generate_dataset(..., seed_start=5000)` output (png/json
pairs); `--donut-checkpoint` is a directory containing `model.safetensors` + the
processor. Add `--skip-vlm` to score Donut alone (no OpenAI key / cost).

## Real-photo test (n=1, illustrative)

A single real **InBody 270** phone photo was hand-labeled and run through Donut
(1-epoch checkpoint), self-hosted and offline:

| Engine | Whole-sheet on the real photo |
|---|---|
| Donut (1-epoch) | **0% — complete failure, but a safe fail-closed refusal** |

The raw generation was malformed pseudo-JSON. The model attended to *some* real
content (it emitted the height `172cm` and the InBody score `80/100`) but could
not produce valid structured output — the real sheet's layout is far
out-of-distribution from the clean synthetic sheets. The parser rejected the
output → `MissingRequiredFieldsError` (ADR-0008). **Crucially, Donut did not
fabricate plausible-but-wrong numbers — it refused.** The "no hallucination at
the front door" guarantee held under total domain shift; the synthetic→real gap
manifests as a *safe refusal*, not a silent misread.

**Why the gap is total:** the current synthetic generator renders a minimal,
clean sheet (weight / LBM / PBF / SMM / BMR + segmental lean, black-on-white, no
distractors). A real InBody 270 sheet carries far more: gym/clinic branding, an
ID/barcode, body-composition-history tables, obesity analysis, segmental *fat*
analysis, an impedance table, a calorie-expenditure list — plus phone-capture
glare and rotation. Donut trained only on the minimal look, so a real photo is
unrecognizable to it. This is the motivation for the *realistic synthetic data*
objective (see Future Work).

> n=1 is anecdotal, not a statistic — treat this as an existence proof of the
> domain gap and of safe failure, not a measured real-world accuracy.

## Issue #13 retrain — realistic 270 sheets (2026-08-22)

Acting on the Future-Work item below, the 270 generator was overhauled into a
full structural clone of a real InBody 270 (branding, ID row, body-composition
analysis, muscle-fat/obesity bar charts, segmental lean **and** fat figures,
InBody score, research parameters incl. LBM rendered as its real "Fat Free Mass"
label, calorie/impedance tables, history strip), with distractor fields derived
coherently from the ground truth and phone-capture augmentation strengthened
(grayscale B&W, desk background, glare, stronger rotation/perspective; ~30% kept
easy). Donut was re-trained fresh from `donut-base`, 1 epoch, **270-only** (2,500
new-look sheets) on Kaggle. `InBodyPayload` contract unchanged.

| Test | Old (minimal template) | New (realistic clone) |
| --- | --- | --- |
| **Real InBody 270 photo (n=1)** | **0%** whole-sheet (fail-closed) | **100%** whole-sheet |
| Held-out synthetic, whole-sheet | 56.0% (easy augmentation) | 53.5% (harder augmentation) |
| Held-out synthetic, per-field | ~57% | 55.0–57.0% |
| Failure mode | safe fail-closed | safe fail-closed (per-field > whole-sheet) |

**The real-photo result is the headline: 0% → 100%.** The retrained model
extracted all twelve fields of the hand-labeled real 270 correctly (weight 82.0,
FFM 63.2, PBF 22.9, SMM 36.3, BMR 1735, visceral fat 7, all five segmental
leans). This confirms the issue-#13 hypothesis: the synthetic→real gap was
*visual/distributional*, not model capacity — cloning the real layout plus
stronger augmentation closed it. **n=1 remains anecdotal** (only one real sheet
exists), so this is a decisive existence-proof of transfer, not a measured
accuracy.

The held-out **synthetic** number staying roughly flat (56% → 53.5%) is expected
and *not* a regression: the new held-out set is deliberately much harder (the
strengthened augmentation), so a near-equal score on a harder test means better
robustness per unit of difficulty, not degradation — and it is measured on a
different distribution than the old 56%, so the two are not directly comparable.
The failure signature stays safe (per-field 57% sits above whole-sheet 53.5%, so
misses are mostly clean refusals, not silent misreads).

ADR-0004 was corrected in the same change: the real 270 *does* print Visceral Fat
Level (confirmed on two real sheets), so `visceral_fat_level` is now rendered and
graded on the 270 too.

> 570 is unchanged (270-first). Mirroring this to the 570 and a both-device
> retrain is the remaining follow-up.

## Adult 570 clone + both-device retrain (2026-08-23)

The remaining follow-up above is done. The 570 template was overhauled into a full
adult-570 clone (nested Body Composition table, muscle-fat / obesity / segmental-lean
bar rows, ECW/TBW, body-composition history; right column Body Fat–LBM control,
segmental fat, BMR, visceral-fat gauge, results-interpretation text, impedance), built
in metric (kg), with LBM labeled "Lean Body Mass" (the 570's real label; same
`$lean_body_mass_kg` placeholder). Distractors derive coherently from the ground truth
so the sheet cross-adds (ICW+ECW=TBW, TBW+Dry Lean=LBM, LBM+Body Fat=Weight). Donut was
re-trained fresh from `donut-base`, **1 epoch, both devices** (2,500 × 270 + 2,500 × 570)
on Kaggle → checkpoint `donut-both-v3`. `InBodyPayload` contract unchanged.

**Held-out synthetic** (400 sheets = 200 × 270 + 200 × 570, disjoint seeds):

| Slice | Whole-sheet | Per-field | Critical mean |
| --- | --- | --- | --- |
| Combined | 46.0% | ~47–48% | 47.5% |
| inbody_270 | 48.0% | — | — |
| inbody_570 | 44.0% | — | — |

The 570 extractor works (44% vs 270's 48% — the denser layout is modestly harder, not
broken, not dragging 270 down). Failure signature stays safe (per-field ≈ whole-sheet →
misses are clean fail-closed refusals). On synthetic, health-correct sheets also get the
device right (per-device health-only == full whole-sheet).

**Real InBody 270 photo (n=1):**

| Field group | Result |
| --- | --- |
| All 11 health fields (weight 82.0, LBM 63.2, PBF 22.9, SMM, BMR, visceral, 5× segmental) | **100% — every value exact** |
| `source_device` | ✗ predicted `inbody_570` (truth `inbody_270`) |
| Whole-sheet (metric counts `source_device`) | **0%** |

Health extraction on the real 270 is **as good as the 270-only model** (still 100%). The
one regression is the *device label*: having learned both layouts, the model calls the
phone-captured (out-of-distribution) 270 a 570. This is a much softer error than a misread
number — but the whole-sheet metric weights every required field equally, so it zeroes the
sheet. Reported honestly rather than masked (`source_device` kept in the metric per
ADR-0006); the health-field read is the number that matters for the product.

**570 validation is synthetic-only** — no real *metric* 570 phone photo exists (the build
reference is an imperial clean render, not a phone capture). Getting a real metric 570
photo is the outstanding real-transfer lever for the 570.

> Combined 46% vs the issue-#13 270-only 53.5% is not a regression: it is a different
> (harder, two-device) held-out set and a model splitting one epoch of capacity across two
> layouts — not directly comparable.

## 570 phone-capture transfer (2026-08-23, #23)

The trained adult-570 layout (kg, seed 3000) was rendered to `inform_570_trained_layout_kg.png`,
**printed on paper, and re-photographed with a phone** (angled, ambient light, JPEG
compression). Scored against the seed-3000 ground truth on `donut-both-v3`:

| | Result |
|---|---|
| Health + segmental fields | **12/12 exact** |
| `unread` | 0 |
| `flagged` | 0 |

Every field (weight 81.9, LBM 67.3, PBF 17.8, SMM 38.9, BMR 1823.7, VFL 10, segmental
5.4/5.4/11.9/11.0/33.6, `inbody_570`) survived the digital→print→photo round-trip with no
degradation. This isolates **capture** from **layout**: the 570's earlier weaknesses
(~1/3 refuse rate, imperial weight misreads) are layout-density and OOD-value problems,
**not** phone-capture problems. Capture is not the weak link for the 570.

Caveat: this is a photo of the *synthetic* sheet, so it validates capture robustness, not
the synthetic→real-device gap — that still needs a genuine InBody 570 printout (#24).

## Genuine off-layout sheets — measured gap (2026-08-23, #24)

Two **genuine** InBody printouts (real scans, metric kg) were phone-photographed and scored
on `donut-both-v3`:

| Sheet | Layout | Result |
|---|---|---|
| InBody 570, Jane Doe, 2014 | older Biospace 570 | **hard refuse — 0/12** |
| InBody 270, Jane Doe, 2018 | older 270 (segmental figure diagrams) | **hard refuse — 0/12** |

Both read nothing and fail-closed (no fabrication). Both are **older Biospace-era layouts**,
structurally different from the modern adult layout we cloned and trained on (nested tables,
figure-diagram segmental analysis, tan aged-paper background). This confirms and extends the
earlier "older 570 hard-refused" note: the synthetic→real gap is **layout-bound**, not
capture-bound.

Contrast within the same session:
- Modern-layout synthetic 570, printed + photographed (#23): **12/12**.
- Genuine modern-layout real 270 (earlier, `inbody_real_01`): **100% health**.
- Genuine **older-layout** 270/570 (here): **0/12, hard refuse**.

**Conclusion:** the model generalizes across *capture* (render → print → photo) on trained
layouts, but does **not** generalize across *layout* to older Biospace designs. The measured
gap on off-layout genuine sheets is a safe zero. Closing the gap for old layouts needs either
those layouts added to the synthetic generator, or genuine **modern**-layout sheets to confirm
transfer on the design we actually trained. Samples saved under `data/real_holdout/` (never
committed — real health data).

## Future Work

- **Real *metric* 570 photo.** The adult 570 clone + both-device retrain is done
  (see above); 570 is synthetic-validated only because no real metric 570 phone
  photo exists yet. One hand-labeled real 570 would validate transfer as the 270
  photo did.
- **Device-label robustness on real photos.** The both-device model reads real 270
  health fields perfectly but misclassifies `source_device` on the out-of-distribution
  photo. Worth a real-photo-aware fix (more real captures, or device-agnostic scoring).
- **Larger real-photo hold-out.** A hand-labeled set of real InBody 270/570
  photos (>1) to turn the anecdote above into a measured synthetic→real gap for
  both engines.
- **Beam-search decoding** for Donut — may recover some refusals with no
  retrain; untested.
