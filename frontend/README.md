# InForm — frontend

The mobile-shaped web app for InForm, built from the Figma design (`InForm` file,
"Hero page" and onward). This is the Track B walking skeleton — see
[issue #31](https://github.com/QeekOw/InForm/issues/31) and
[issue #29](https://github.com/QeekOw/InForm/issues/29) for the full spec.

Next.js 16 (App Router, Turbopack), TypeScript, Tailwind v4. No component library,
no external state management library — plain React state plus ephemeral `sessionStorage`
(see `lib/`) is used during the client-side intake and review session.

## What actually works right now

The **Profile → real computed targets** path is fully wired end to end
([issue #34](https://github.com/QeekOw/InForm/issues/34)):

1. `/profile` — a real form (name, date of birth, biological sex, activity level,
   goal). Date of birth is validated (13–100 years old) before you can continue —
   nothing gets sent anywhere on an implausible age.
2. `/upload` → `/upload/capture` → `/upload/analyzing` — the InBody-sheet flow.
   Module 1's Donut model is deployed to Hugging Face Hub & Space ([issue #33](https://github.com/QeekOw/InForm/issues/33) / PR #51),
   with live browser pipeline integration in PR #57. Currently, these screens handle
   sheet type selection, camera capture, file upload (including PDF documents),
   and an analyzing state transition.
3. `/preview` and `/preview/edit` — show baseline InBody reading values
   (`lib/inbody.ts`'s `DEFAULT_READING`) clearly marked as demo defaults, which
   you can review or hand-edit field by field (including optional `visceral_fat_level`).
   Upon confirming, the temporary uploaded photo is cleared per ADR-0011 §3.
4. `/result` — POSTs your Profile and the confirmed reading to the backend's
   `POST /plan`, which calls `inform.nutrition_engine.compute_targets`
   and `inform.exercise_filter.recommend_exercises` — real Katch-McArdle BMR, real
   TDEE, real macro split, and real bilateral-asymmetry detection choosing corrective
   exercises. The numbers on this screen are genuinely computed by the deterministic
   pipeline.

`/sign-in` renders the login screen with guest continuation; accounts persistence lands
in issues #41–44.

## Deployment & State

- **Deployment**: Deployed on Vercel from the repository's `main` branch, connecting to
  the Render backend API via `NEXT_PUBLIC_API_URL`.
- **Session state & Privacy**: Client session state is carried transiently via `sessionStorage`.
  Per **ADR-0011 §3 (Zero Image Persistence for User Uploads)**, uploaded sheet photos
  are kept only in browser memory during review and are permanently removed from session
  storage when the user confirms their scan on the preview screen.

## Project layout

```
app/
  page.tsx                 Hero / landing
  sign-in/                 Login screen (UI and guest entry)
  profile/                 Intake form -> real UserProfile
  upload/                  Choose sheet type + upload (image / PDF)
  upload/capture/          Camera viewfinder
  upload/analyzing/        Simulated OCR wait, auto-advances
  preview/                 Review the InBody reading
  preview/edit/            Hand-edit every field (supports optional visceral fat)
  result/                  Calls POST /plan, renders the real computed plan
components/
  PhoneFrame.tsx           Shared phone-width column every screen sits in
  ApiStatus.tsx            "Backend: online/unreachable" live status indicator
  ReportPhoto.tsx          Ephemeral sheet review photo / ADR-0011 privacy badge
lib/
  config.ts                Centralized runtime config (API_URL)
  exercise.ts              Exercise, ExercisePlan, and MovementType models
  inbody.ts                InBodyPayload schema, field metadata, and defaults
  photo.ts                 Downscaling, camera capture, and PDF preview helpers
  session.ts               sessionStorage read/write and removal helpers
  user.ts                  UserProfile schema and activity multiplier mappings
```

## Running locally

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, defaults to localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend (see
`../backend/README.md`) needs to be running for `/result` to return real
numbers — without it, `/result` displays a clear "couldn't reach the API" state
rather than fabricating anything.

Run tests and verification:
```bash
npm run lint
npm run build
```
