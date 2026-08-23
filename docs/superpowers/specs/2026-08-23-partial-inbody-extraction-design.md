# Partial InBody Extraction — Design

**Date:** 2026-08-23
**Module:** 1 (OCR)
**Status:** Approved (brainstorming), pending implementation plan
**Amends:** ADR-0008 (OCR failure handling)

## Problem

Today extraction is strictly fail-closed (ADR-0008): if any single required field is
unreadable, or a cross-check fails, the whole extraction is discarded and the user is asked to
re-upload. On a real phone photo where only one field is glare-washed, the user loses every
other correctly-read value. We want to **extract every field the model can read, and return a
structured list of the fields that failed** (unreadable, or cross-check-suspect), so the UI can
notify the user without throwing away good data.

The **no-fabrication guarantee stays intact**: we never invent a value to fill a gap. Unread
fields carry no value; flagged fields are genuine reads marked low-confidence.

## Decisions (locked in brainstorming)

1. **Notification scope:** the extraction layer returns a *structured* result (read values +
   failed-field lists). Rendering an on-screen notification is the UI/frontend's job — out of
   this module's scope.
2. **Cross-check breach → flag, don't reject.** When the sheet's own math disagrees (read LBM ≠
   weight×(1−PBF/100), or printed BMR ≠ Katch–McArdle recompute), keep the read values and add
   the involved fields to a `flagged` list ("verify"). We can't isolate the single culprit, so
   all involved fields are flagged.
3. **Floor case → still fail closed.** If *zero* required fields are read (non-InBody image, or
   a photo too corrupted to read anything), raise as today — partial extraction only applies
   when some real data was read.
4. **No fabrication.** Unread → no value; flagged → real read, low-confidence.

## Architecture (Approach A — typed partial result)

### Data model (`inform/inbody.py`)

`InBodyPayload` and `SegmentalLean` are unchanged — they remain the "complete and validated"
contract downstream consumers (Module 4) require. Add:

```python
class PartialSegmentalLean(BaseModel):   # all Optional
    left_arm_kg: float | None = None
    right_arm_kg: float | None = None
    left_leg_kg: float | None = None
    right_leg_kg: float | None = None
    trunk_kg: float | None = None

class PartialInBody(BaseModel):          # holds what was read; None = unread
    weight_kg: float | None = None
    lean_body_mass_kg: float | None = None
    percent_body_fat: float | None = None
    skeletal_muscle_mass_kg: float | None = None
    basal_metabolic_rate_kcal: float | None = None
    segmental_lean: PartialSegmentalLean | None = None
    visceral_fat_level: int | None = None
    source_device: Literal["inbody_270", "inbody_570"] | None = None

class InBodyExtraction(BaseModel):
    data: PartialInBody
    unread: list[str]     # required fields (dotted for segmental) that were None
    flagged: list[str]    # fields read but cross-check-suspect
    def is_complete(self) -> bool:        # not unread and not flagged
        ...
    def as_payload(self) -> InBodyPayload | None:  # promote when complete, else None
        ...
```

`unread`/`flagged` use dotted names for segmental fields (`segmental_lean.left_arm_kg`),
matching the eval harness convention.

### Engine contract (`inform/engines/*.py`)

`Engine = Callable[[Path], PartialInBody]` — engines return what they read, `None` for the rest.

- **VLM (`vlm.py`):** `is_inbody_sheet=false` → still raises `NotAnInBodySheetError` (explicit
  non-sheet signal). Otherwise map `_RawExtraction` → `PartialInBody` and return it. The engine
  no longer raises `MissingRequiredFieldsError`; it simply leaves unread fields `None`. (The
  raw extraction model already reads into nullable slots — this is a small change.)
- **Donut (`donut.py`):** malformed JSON → empty `PartialInBody` (all `None`). Valid JSON →
  parse into `PartialInBody`, keeping whatever keys are present. `_to_payload` becomes
  `_to_partial`; it no longer raises `MissingRequiredFieldsError`.

### Seam (`inform/extract.py`)

`extract_inbody(image_path, engine=vlm.extract) -> InBodyExtraction`:

```
partial = engine(path)                         # may raise NotAnInBodySheetError (VLM only)
unread  = [f for f in REQUIRED_FIELDS+segmental if <partial value is None>]
if len(unread) == total_required:              # floor: nothing read
    raise MissingRequiredFieldsError(unread)   # fail closed, re-upload
flagged = _cross_check(partial)                # [] or implicated field names
return InBodyExtraction(data=partial, unread=unread, flagged=flagged)
```

`_cross_check` changes from **raising** to **returning** a list of implicated field names, and
runs each check only when its inputs are all present:
- LBM check (inputs weight_kg, percent_body_fat, lean_body_mass_kg): breach →
  flags `["weight_kg", "percent_body_fat", "lean_body_mass_kg"]`.
- BMR check (inputs basal_metabolic_rate_kcal, lean_body_mass_kg): breach →
  flags `["basal_metabolic_rate_kcal", "lean_body_mass_kg"]`.
- Return the de-duplicated union.

### Error handling

Unchanged guarantee — never fabricates. Two hard-reject paths remain:
- `NotAnInBodySheetError` — VLM's explicit non-sheet signal.
- `MissingRequiredFieldsError` — floor case (nothing readable), raised by the seam.

`CrossCheckFailedError` is **removed** — nothing raises it once the cross-check flags instead
of rejecting. Delete the class from `errors.py` and update any references (tests, imports).

### Eval harness (`inform/evaluate.py`, `inform/compare.py`)

`evaluate` consumes `InBodyExtraction` through the real seam (so it exercises cross-checks).
- **Per-field:** credit each field that is read AND correct (within ±0.1). A partially-read
  sheet now scores its good fields instead of zero.
- **whole_sheet:** all required fields read, all correct, and no flags.
- **Floor-case raise / non-sheet raise:** scored as all required fields wrong (as today).

`compare.py` wires the engine into the seam:
`lambda p: extract_inbody(p, engine=donut_engine)`.

**Comparability caveat (documented, not hidden):** crediting partial reads raises per-field
numbers versus the old all-or-nothing scoring. Prior numbers (e.g. the both-device v3 46%
whole-sheet) are not directly comparable to a partial-scored number. This will be stated in the
eval writeup and the ADR amendment.

## Testing

Adapt `test_fail_closed.py`, `test_donut.py`, `test_evaluate.py`. New/updated cases:
- Partial read → returns the read values and lists the unread required fields.
- Cross-check breach → the involved fields appear in `flagged` (no exception raised).
- Floor case (nothing readable) → raises `MissingRequiredFieldsError`.
- Non-InBody image (VLM `is_inbody_sheet=false`) → raises `NotAnInBodySheetError`.
- `is_complete()` true only when no unread and no flagged; `as_payload()` promotes a complete
  extraction to a validated `InBodyPayload`, returns `None` otherwise.

## Scope / rollout

- This is its **own branch/PR** (`feat/partial-extraction`), independent of the in-flight 570
  work — it touches `extract.py`, the engines, `evaluate.py`, `inbody.py`, and tests, none of
  which the 570 branch changes.
- **ADR-0008 amended** to record the shift from hard fail-closed to "partial + flag," with the
  no-fabrication guarantee preserved and the two remaining hard-reject paths named.

## Out of scope

- The user-facing notification UI (frontend's job).
- Changing `InBodyPayload` itself (stays the complete/validated downstream contract).
- Any change to Module 2/3/4.
