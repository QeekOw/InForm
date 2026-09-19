# InForm — frontend

The mobile-shaped web app for InForm, built from the Figma design (`InForm` file,
"Hero page" and onward). This is the Track B walking skeleton; see
[issue #31](https://github.com/QeekOw/InForm/issues/31) and
[issue #29](https://github.com/QeekOw/InForm/issues/29) for the full spec.

Next.js 16 (App Router, Turbopack), TypeScript, Tailwind v4. No component library and
no state management library: plain React state plus `sessionStorage` (see `lib/`)
carries the flow between screens.

## The flow

1. `/` → `/sign-in`. Sign-in isn't built yet (accounts are Phase 2,
   [issue #41](https://github.com/QeekOw/InForm/issues/41)). Log In shows an error for an
   empty email or password, and email, Google, Apple and Facebook sign-in all say they
   aren't available yet instead of doing nothing.
2. **Continue as a Guest** goes straight to `/upload`. **Sign Up** goes to `/profile`
   first.
3. `/upload` shows the Sample Gallery ([issue #35](https://github.com/QeekOw/InForm/issues/35)):
   picking a sheet loads its pre-computed read from the backend's `/samples` endpoints. A
   clean read goes straight to `/result`; anything unread, flagged or refused stops at
   `/preview`. Uploading your own photo or PDF goes through `/upload/capture` or
   `/upload/analyzing` instead. No model reads it yet: Analyzing waits three seconds over
   the photo and moves on, and PDFs show a placeholder instead of a photo.
4. `/preview` shows the picked sheet's read with flagged fields marked, or, for an upload,
   `DEFAULT_READING` from `lib/inbody.ts` labelled as demo values. `/preview/edit` won't
   confirm while a required field is blank; Visceral Fat Level is the only optional field
   (ADR-0004).
5. Confirm drops the photo from `sessionStorage` (ADR-0011 §3). A guest without a Profile
   fills in `/profile` next.
6. `/result` POSTs the Profile to the backend's `POST /plan` with either the `sample_id`
   of a clean, unedited Sample sheet (the backend plans from its stored read and refuses
   an unread, flagged or refused one) or the confirmed reading. The backend runs
   `inform.nutrition_engine.compute_targets` and
   `inform.exercise_filter.recommend_exercises`. The screen says when the numbers came
   from the demo reading.

`/profile` validates the date of birth (13–100 years old,
[issue #34](https://github.com/QeekOw/InForm/issues/34)) and offers the five activity
levels with how often each one trains.

## Deployment

- **Frontend:** Vercel project `in-form`, root directory `frontend`. Production deploys
  from `feat/web-walking-skeleton`, which is kept level with `main`; switching it to
  `main` is a dashboard setting (Settings → Environments → Production). `NEXT_PUBLIC_API_URL`
  must point at the backend; `next.config.ts` fails any Vercel build that doesn't set it.
- **Backend:** Render; see `../backend/README.md`.

## Known gaps

- Device compatibility: exclusively accepts and parses **InBody 270** result sheets only (other models like InBody 570 or 770 are not supported).
- No OCR on uploads: every reading starts from the demo values.
- No accounts, sign-in or saved history ([issues #41–44](https://github.com/QeekOw/InForm/issues/41)).
- "Forgot Password?" is design copy only.

## Project layout

```
app/
  page.tsx                 Hero / landing
  sign-in/                 Login screen (validation, guest entry; sign-in not built)
  profile/                 Intake form -> real UserProfile
  upload/                  Sample Gallery + upload (image / PDF)
  upload/capture/          Camera viewfinder
  upload/analyzing/        Simulated wait over the uploaded photo
  preview/                 Review the reading
  preview/edit/            Hand-edit every field
  result/                  Calls POST /plan, renders the computed plan
components/
  PhoneFrame.tsx           Shared phone-width column every screen sits in
  ApiStatus.tsx            "Backend: online/unreachable" live status pill
  ReportPhoto.tsx          The uploaded photo, or a placeholder when there isn't one
lib/
  config.ts                API_URL
  exercise.ts              Exercise / ExercisePlan types
  flow.ts                  Where Confirm and Profile go next (guest flow)
  inbody.ts                InBodyPayload types, field metadata, demo reading
  photo.ts                 Downscaling, camera capture, PDF placeholder
  session.ts               sessionStorage keys and helpers
  user.ts                  UserProfile types and activity levels
public/brand/
  inform-logo-on-dark.png  Logo for dark backgrounds (source: docs/assets/InForm.png)
```

## Running locally

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, defaults to localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The backend (see
`../backend/README.md`) needs to be running for `/result` to return real numbers.
Without it, `/result` shows a clear "couldn't reach the API" state rather than
fabricating anything.

Before pushing:

```bash
npm run lint
npm run build
```
