# ADR-0011: Health Data at Rest: Samples Redaction and Zero Image Persistence

**Status:** Accepted
**Date:** 2026-09-13
**Module:** Cross-cutting (Privacy, Samples Gallery, Storage)

## Context

InBody result sheets contain Personal Health Information (PHI), including subject/member
identifiers, gym or clinic branding, age, gender, and detailed physiological body composition
measurements.

The product needs a public gallery of Sample sheets so visitors can experience immediate
extraction and plan synthesis without uploading their own data. The gallery includes both
synthetic sheets and real InBody printouts held with subject consent.

Additionally, unredacted real test scans exist locally for model evaluation and calibration,
and real users will upload their own InBody photos during Phase 3. A rigorous privacy posture
is required to prevent accidental or systematic leakage of personal health data at rest.

## Decision

1. **Permanent Redaction of Gallery Printouts**:
   - Any real InBody printout placed in the public sample gallery (`data/samples/`) must have
     all Personal Health Identifiers (specifically Member ID and Gym/Facility Name)
     permanently blanked out with solid fills prior to being committed.
   - Redactions are verified by automated tests inspecting bounding box pixel uniformity.
   - Physiological metrics (weight, body fat, muscle mass, etc.) remain intact for model
     extraction.

2. **Raw Holdout Data Excluded from Version Control**:
   - Raw, unredacted real scans used for holdout evaluation remain strictly on local
     workstations in `data/real_holdout/`.
   - `data/real_holdout/` is permanently excluded via `.gitignore`.

3. **Zero Image Persistence for User Uploads**:
   - Uploaded sheet images are processed transiently in memory for the duration of the
     extraction review session.
   - No uploaded user photo is ever written to disk, a relational database, an object store,
     or persistent logs.
   - Once the user confirms or saves their Scan, only the structured numeric extraction
     payload is persisted.

## Consequences

- **Verifiable Privacy**: Real samples in public git history cannot expose member IDs or gym
  affiliations.
- **Zero Retention Exposure**: Because no uploaded images are stored at rest, database breaches
  cannot expose personal photographs or printouts.
- **Automated Guardrails**: Test suites enforce pixel-level redaction on any manifest item
  marked with provenance `real`.
