# InForm — frontend

The mobile-shaped web app for InForm, built from the Figma design (`InForm` file,
"Hero page" and onward). This is the Track B walking skeleton — see
[issue #31](https://github.com/QeekOw/InForm/issues/31) and
[issue #29](https://github.com/QeekOw/InForm/issues/29) for the full spec.

Next.js 16 (App Router, Turbopack), TypeScript, Tailwind v4. No component library,
no state management library — the design is a handful of screens, so plain React
state plus `sessionStorage` (see `lib/`) is enough for now.

## What actually works right now

The **Profile → real computed targets** path is fully wired end to end
([issue #34](https://github.com/QeekOw/InForm/issues/34)):

1. `/profile` — a real form (name, date of birth, biological sex, activity level,
   goal). Date of birth is validated (13–100 years old) before you can continue —
   nothing gets sent anywhere on an implausible age.
2. `/upload` → `/upload/capture` → `/upload/analyzing` — the InBody-sheet flow.
   No OCR runs here (Module 1 needs a 776 MB Donut checkpoint that isn't deployed
   anywhere yet — see [issue #33](https://github.com/QeekOw/InForm/issues/33)), so
   these screens are UI-only: picking a sheet type, opening the camera viewfinder,
   and a simulated "analyzing" wait all just advance the flow.
3. `/preview` and `/preview/edit` — show a fixed, seeded InBody reading
   (`lib/inbody.ts`'s `DEFAULT_READING`) that you can review or hand-edit field by
   field. This *is* the real correction-flow shape (a person typing in what the
   sheet says), just without a model behind it yet.
4. `/result` — POSTs your Profile and the (possibly edited) reading to the backend's
   `POST /plan`, which calls the actual `inform.nutrition_engine.compute_targets`
   and `inform.exercise_filter.recommend_exercises` — real Katch-McArdle BMR, real
   TDEE, real macro split, real bilateral-asymmetry detection choosing corrective
   exercises. The numbers on this screen are genuinely computed, not display copy.

`/sign-in` renders the login screen from the design but isn't wired to anything —
there's no accounts backend yet ([issues #41–44](https://github.com/QeekOw/InForm/issues/41)).

## What's carrying state between screens

There's no backend session or database yet, so `lib/session.ts` + `lib/inbody.ts`
carry the Profile and the InBody reading across routes via `sessionStorage`
(cleared when the tab closes). `SESSION_KEYS` in `lib/inbody.ts` is the single
source of truth for the storage keys — add new state there, not as raw string
literals.

## Known gaps

- **Not deployed.** This only runs locally right now (`npm run dev`). Issue #31's
  actual acceptance criteria (a public URL, deployed from the repo) aren't met yet
  — that's deliberate, deployment is being held off for now.
- **No real OCR.** Everything from "upload a sheet" through "here's what we read"
  is either a placeholder or a fixed seed value, not a model output.
- **No sample sheet gallery** ([issue #35](https://github.com/QeekOw/InForm/issues/35)) —
  blocked on [#32](https://github.com/QeekOw/InForm/issues/32), which hasn't started.
- **No accounts, no history, no persistence** — everything lives in one browser tab.
- Two Figma screens (camera capture, and the report-photo cards on
  Preview/Result) show a placeholder instead of the design's real photo — the
  Figma mock used an actual InBody printout with a visible gym name and member ID,
  which the project's Track B privacy stance says should never ship in the app.

## Running locally

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, defaults to localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend (see
`../backend/README.md`) needs to be running too for `/result` to return real
numbers — without it, `/result` shows a clear "couldn't reach the API" state
rather than fabricating anything.

`npm run lint` and `npm run build` are both clean as of this writing (9 static
routes, no type errors).

## Project layout

```
app/
  page.tsx                 Hero / landing
  sign-in/                 Login screen (UI only, not wired)
  profile/                 Sign-up / intake form -> real UserProfile
  upload/                  Choose sheet type + upload (UI only)
  upload/capture/          Camera viewfinder (UI only)
  upload/analyzing/        Simulated OCR wait, auto-advances
  preview/                 Review the (seeded) InBody reading
  preview/edit/            Hand-edit every field
  result/                  Calls POST /plan, renders the real computed plan
components/
  PhoneFrame.tsx            Shared phone-width column every screen sits in
  ApiStatus.tsx             Small "Backend: online/unreachable" live status pill
lib/
  session.ts                sessionStorage read/write helpers
  inbody.ts                 Types mirroring inform's UserProfile/InBodyPayload,
                             the seed reading, and the session-key registry
```
