# Revision 1 — what to do next

English reference copy of `ui-brief-revisi-1-id.md`, which is the version the designer
works from. Follows on from `frontend-ui-brief.md`; it does not repeat that document,
only what changed after the first mockups and after we measured how often the model
actually reads a real InBody sheet.

The first mockups are good and most of them stand. What follows is mostly things we
never told her.

---

## 0. Urgent: replace the real sheet photographs

The camera screen, the "Analyzing" screen and the Preview screen all use a **genuine
InBody printout belonging to a real person**. The gym name and member ID are legible.

That is personal health data, and mockups end up in decks, portfolios and READMEs. Once
it circulates it cannot be pulled back.

**Action:** swap in `real_270_redacted.png` from the designer packet (identity blacked
out) or a sheet from our synthetic generator. Applies to the two 270/570 thumbnails on
the report-selection screen as well.

Quick, but do it before the mockups go to anyone.

---

## 1. A failed-read screen — the most important item

The flow as drawn is Camera → Analyzing → Preview. It always succeeds.

It does not. We measured twelve genuine InBody photographs: **six were not read at all.**
Half.

So the screen that does not exist is the one most users currently see.

This is not a bug that will be fixed and disappear. The system is designed this way: when
the model is not confident it **refuses** rather than guessing. Saying "we could not read
this" beats emitting a wrong number and building a training plan on it. The screen is
permanent.

**To design:**

- One screen for "we could not read this sheet".
- Tone: **not the user's fault.** No red error iconography, nothing that reads as a crash.
  This is an ordinary outcome, not a failure.
- Briefly say why, in actionable terms — low light, shadow, a folded sheet, a skewed
  angle, part of the page cut off.
- Give a clear way forward. At minimum: retake. Consider also uploading from the gallery,
  or trying a sample sheet so the user still sees the app work.
- If possible, connect it back to the camera guidance — someone who failed once should be
  told what to change, not asked to repeat blind.

If only one item from this document gets done, this is it.

---

## 2. Preview: not every number is equal

The Preview screen with Edit and Confirm is the right idea and should stay. But every
number currently carries identical visual weight, as if all were equally certain. They
are not.

Three distinct states, distinguishable at a glance:

**a. Read cleanly.** The model read it and nothing contradicts it.

**b. Flagged.** The model read it but our cross-check disagrees. Real example: on one
sheet the model read Lean Body Mass as 30.0 kg where weight and body-fat percentage imply
about 62.5 kg. Still show the number, but the user needs to know it is **suspect** and
worth checking against the printout.

**c. Unread.** The model produced nothing for that field. Empty. The user fills it in or
proceeds without it.

These three must not look the same.

**One important note on tone.** Do not make a cleanly-read field look **verified** — no
green ticks, no "confirmed" labels. We found cases where the model is wrong but the value
is still plausible: arms printed as 3.53 and 3.50 were read as 3.5 and 3.7. Nobody can
catch that by eye, and neither can our cross-checks. If the display implies the number is
guaranteed, the user is *less* likely to check it — which is exactly the moment we need
them to. Neutral beats reassuring.

The Segmental Lean Analysis block (four limbs) is both the most error-prone and the least
protected. If one block should invite scrutiny more than the others, that is the one.

---

## 3. What is already right — do not change it

So none of it is lost in revision:

- **The 270 / 570 choice before upload.** Not just tidy UI — it directly helps the
  backend, which no longer has to infer the sheet type. Keep it.
- **The camera guidance overlay.** Precisely the intervention that reduces the failure
  rate in item 1.
- **"Continue as Guest".** Matches the plan: the app must be fully usable before anyone
  creates an account.
- **The "Analyzing your body composition" screen.** The read genuinely takes ~45 seconds,
  so this screen is necessary and is sized about right.

---

## 4. Settled — no longer an open question

**Interface language: English.** Everything the user reads — buttons, labels, error
messages, the AI-written paragraph — is in English. Her documents stay in Indonesian.

---

## 5. Deferred

The **sheet-layout specification** task (`DESIGNER-BRIEF-sheet-layout.md`) still stands
but drops **below** items 1 and 2 here. Its output is only usable after a retrain, and
the retrain is queued behind GPU availability, whereas items 1 and 2 block three
developers now.

One task from that brief is **cancelled**: the visual comparison of the BMI and Fat Free
Mass positions. We tested the hypothesis ourselves and it was wrong.

If the layout task does get picked up, one addition: measure the **horizontal gap and
alignment between the adjacent "Segmental Lean Analysis" and "Segmental Fat Analysis"
panels**. We found the model sometimes reads straight rightward and crosses from one
panel into the other, so the horizontal relationship between them turns out to matter.

---

## Suggested order

1. Replace the real sheet photos (item 0) — quick, but first.
2. The failed-read screen (item 1).
3. The three field states on Preview (item 2).
4. The Result screen — still empty in the mockups, and we have not briefed it. Separate
   conversation.
5. The sheet-layout spec (item 5), later.

If anything here is unclear or seems to contradict the main brief, ask before building —
it is far more likely we wrote it badly than that she read it wrong.
