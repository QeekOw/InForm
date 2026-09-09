# ADR-0011: Storing health data at rest — samples first, extractions not images

**Status:** Accepted (supersedes the inference-privacy scope of
[ADR-0005](0005-inference-privacy-posture.md); that ADR's training-data and
self-hosting conclusions still stand)
**Date:** 2026-09-09
**Module:** the application layer around Modules 1–4

## Context

InForm gained **accounts** and **history**: one Account per person, Scans accumulating over
time so someone can see their body composition change. That turns a pipeline which computed
in memory and forgot into a system holding body composition — weight, PBF, lean mass, age,
biological sex — **against an identity, indefinitely**.

ADR-0005 drew its boundary for a system that stored nothing: "POC only, synthetic or
consented data, never real PHI," with compliance infrastructure deferred as future work. That
no longer describes the system, and a stale ADR marked Accepted is worse than none because
people trust it.

The product is still a portfolio piece, not a medical service. So the goal is not a
compliance programme; it is a posture that is honest, defensible, and small enough to
actually implement.

## Decision

- **v1 reads sample sheets only.** The gallery holds sheets we provide — synthetic ones plus
  real printouts we hold with the subject's consent, labeled as which. No stranger's health
  data enters the system at all.
- **Upload is phase 2, and is consented by construction.** The upload screen states plainly
  that this is a student project and what happens to the data. Consent is the word in
  ADR-0005 that makes real sheets permissible, so it has to be real consent, not fine print.
- **The uploaded image is never persisted.** It lives only for the session, because the
  show-and-correct flow needs to display the sheet beside the extracted numbers for review.
  Once the Scan is saved, the image is discarded. It is never written to a database, an
  object store, or a log.
- **Only extracted values are stored**, on the Scan, with the Profile used and the Plan
  produced. Scans are immutable; a value a person typed is recorded as a **corrected field**
  rather than overwriting the machine's read.
- **Account deletion removes everything** — Account, Scans, Plans. No soft delete, no
  retained analytics copy.

## Considered Options

- **Store the uploaded image.** Rejected. It is the most identifying artifact in the system
  (it carries a member ID, a gym name, a test date and a full body-composition report), and
  nothing in the product needs it after extraction.
- **Keep uploads anonymous — no account attachment.** Rejected: it defeats History, which is
  the only reason accounts exist.
- **Defer the whole question until upload ships.** Rejected. The schema is being written now,
  and retrofitting a data-retention posture onto a live schema is exactly the mistake this
  ADR exists to avoid.

## Consequences

- **Extractions cannot be re-run on past uploads.** Module 1 currently reads 3 of 12 real
  sheets (see `docs/ocr-eval-results.md`) and will improve substantially; discarding the
  image means an old Scan keeps the values it was read with and cannot benefit from a better
  checkpoint. This is a real cost, accepted deliberately: a person can always scan again, and
  the alternative is a permanent store of identifiable health documents.
- The deterministic pipeline is untouched. This is a decision about what the application
  remembers, not about how anything is computed.
- Because corrected fields are recorded rather than merged, History stays auditable: a trend
  line can show which points rest on values a person typed.
