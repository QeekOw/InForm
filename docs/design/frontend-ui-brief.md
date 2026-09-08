# InForm — Frontend UI/UX Brief

A handoff document for the UI designer. It explains what InForm does, who the
frontend is for, the one idea the design has to get right, and a screen-by-screen
map of what needs to be designed. Field names and example numbers here are the
real ones from the product, so please design with them instead of placeholder text.

---

## 1. What InForm is

InForm reads an InBody body-composition scan (the printout you get from the
body scanners in gyms and clinics) and turns it into a concrete daily plan:
how many calories and grams of protein, carbs, fat, and fiber to eat, plus a
workout that targets the person's specific left/right muscle imbalances.

The flow the user goes through:

1. They tell us a few things about themselves (age, sex, activity level, goal).
2. They give us their InBody sheet.
3. We read the numbers off the sheet automatically (this is the OCR step, and
   it is the part we most want to show off).
4. We compute their targets and detect any muscle imbalance.
5. We show them a finished, readable plan.

## 2. Who and what this is for

- **Purpose:** portfolio / showcase piece. The goal is to make the engineering
  look excellent to people who view it (recruiters, reviewers, collaborators).
  It is not a live medical product, so there is no payment and no settings.
  It **does** have accounts, because the product's second idea is progress over
  time: you scan again months later and see what changed.
- **One account, one person.** The account holder is the person the scans are
  about. There is no coach-with-clients mode, no switching between people.
- **Platform:** a **web app**, designed **mobile-first** and presented inside a
  **phone frame** (a phone mockup on the page). It should feel like a phone app,
  but it runs in a browser from a single link. Design for a phone-width screen
  first; a tidy desktop view is a bonus, not the priority.
- **Emphasis:** the **scan-reading (OCR) moment** is the hero of the whole
  experience. More on that below.

## 3. The one idea the design has to get right

Most "AI fitness" apps show you numbers and you have no idea where they came
from. InForm is built the opposite way. **Every number is computed by plain,
auditable code from the scan. The AI only writes the words around those numbers,
and it is never allowed to change one.**

The design should make that trustworthiness *visible*. Two practical ideas for
how to express it (the designer can take these further):

- **Show the receipt.** When we read the sheet, show the scan and the extracted
  numbers together, so the viewer can see that a number on the plan traces back
  to a number on the sheet. The "the machine read this, and here is exactly what
  it saw" moment is the thing to dramatize.
- **Two visual voices.** The hard numbers (calories, macros, imbalance
  percentages) should feel precise, exact, machine-made. The written coaching
  paragraph (the one part the AI wrote) can feel softer and more human. Keeping
  those two visually distinct reinforces the whole point of the product.

## 3b. Two rules the design has to respect

These are not implementation details; they change what screens can and cannot do.

- **A scan is frozen forever.** One scan = the sheet that was read + the four
  facts about the person at that moment + the plan produced. It is never edited.
  Scanning again *adds* a new scan; it never overwrites the last one. So there is
  no "edit this plan" affordance anywhere, and every past plan stays exactly as it
  was computed.
- **The four facts travel with the scan, not with the account.** If someone
  changes their goal from fat loss to build muscle, their old plans keep the goal
  they were actually built with. The account remembers the latest answers only to
  pre-fill the form next time. This is why history can be trusted as a record.

## 4. Tone and visual direction

Open to the designer, but some guardrails:

- This is a health and body-composition product, so it should feel **clean,
  precise, and calm**, closer to a good medical or data tool than to a loud
  consumer fitness app. Trust over hype.
- Numbers are the main content. Typography and layout for **readable data**
  (clear number/label pairs, good hierarchy) matter more than illustration.
- Because the scan reading is the hero, there is room for one genuinely
  memorable moment around the "reading the sheet" step (an animation, a scan
  effect, a reveal). Spend the visual budget there.

## 5. Screens to design (the blueprint)

The core is a short, linear flow. Please design each screen for phone width,
including its loading and error states where noted.

### Screen 0 — Sign in / create account
- Purpose: get the person into their account.
- Keep it as light as possible: this is a showcase, and a heavy sign-up form is
  the fastest way to lose a visitor. Design for the smallest credible thing.
- States to design: signed out, and the error case (wrong details).
- Note: a visitor should be able to *see* what InForm is before being asked to
  sign in. Design screen 1 so it can be reached signed-out.

### Screen 1 — Intro / start
- Purpose: say in one line what InForm does, and start the flow.
- Content: product name, one-sentence explanation, one primary button ("Start"
  or similar). Optionally a small "how it works" of the 4 steps.
- Keep it short. This is a doorway, not a marketing landing page.

### Screen 2 — About you (intake form)
- Purpose: collect the four facts we need about the person.
- Fields (these are exact, please use them):
  - **Age** — a number.
  - **Biological sex** — two choices: **male** / **female**.
  - **Activity level** — a single choice from five levels. Show friendly labels,
    each maps to a number behind the scenes:
    - Sedentary (1.2)
    - Lightly active (1.375)
    - Moderately active (1.55)
    - Very active (1.725)
    - Extremely active (1.9)
  - **Goal** — two choices: **Fat loss** and **Build muscle** (internally
    "fat_loss" and "hypertrophy").
- Design the field controls (steppers, segmented buttons, selectors) for a phone.

### Screen 3 — Provide your scan
- Purpose: the user gives us an InBody sheet to read.
- **For now, design this as "choose a sample sheet"**: a small gallery of
  provided InBody sheets the user picks from, plus a visible (but secondary)
  "upload your own" affordance. Note for the designer: real-photo upload is a
  planned later feature that is not confirmed yet, so please make the sample
  picker the primary path and leave room for an upload button we may enable
  later.
- Content: a few selectable sheet thumbnails, a short line telling the user what
  an InBody sheet looks like, and the primary "Read this sheet" action.

### Screen 4 — Reading the sheet (the hero moment)
- Purpose: show the OCR happening. This is the screen to make memorable.
- Two parts:
  - **A "reading" / in-progress state.** The scan is being read. This is where a
    scan-line animation or progressive reveal fits. It should feel like the
    machine is genuinely working through the sheet.
  - **The extraction result.** Show the sheet next to the numbers we pulled out
    of it, so the connection is obvious. Please design how a single extracted
    value looks (label, value, unit) and how the set reads as a group.
- **Extracted fields to lay out** (real fields from a sheet):
  - Weight (kg)
  - Lean Body Mass / Fat Free Mass (kg)
  - Percent Body Fat (%)
  - Skeletal Muscle Mass (kg)
  - Basal Metabolic Rate (kcal)
  - Visceral Fat Level (a small integer, may be absent)
  - Segmental lean, five values: left arm, right arm, left leg, right leg, trunk (kg each)
  - Source device (e.g. "InBody 570")
- **States to design here:**
  - Normal: every field read cleanly.
  - **Flagged / unread field:** sometimes a value can't be read confidently.
    Please design how one field looks when it is uncertain or missing, distinct
    from a clean read. This honesty about confidence is part of the trust story.

### Screen 5 — Your numbers (computed targets)
- Purpose: show what the code computed from the scan. All hard numbers.
- **Nutrition block** (exact fields):
  - Daily Energy Target (kcal) — the headline number
  - BMR (kcal) and TDEE (kcal) — shown as the supporting basis
  - Protein (g)
  - Carbohydrates (g)
  - Fats (g)
  - Fiber (g)
- **Imbalance block:**
  - Zero, one, or more detected imbalances, each a short human-readable line,
    e.g. "L/R arm lean-mass deviation 11.1%". Design for the empty case (no
    imbalance found) and the one-or-more case.
- This screen should feel exact and trustworthy. These are the audited numbers.

### Screen 6 — Your workout
- Purpose: show the recommended exercises, tied to the imbalances above.
- Each exercise item has: **name**, the **muscle it targets**, and a **type tag**
  which is one of three: *corrective (unilateral)*, *compound (bilateral)*, or
  *cardio (HIIT)*. Please design the exercise row and how the type tag reads.
- Example rows:
  - Single-arm dumbbell row — targets lats — corrective (unilateral)
  - Single-arm overhead press — targets deltoids — corrective (unilateral)
  - Rowing sprint intervals — targets cardio — cardio (HIIT)
- Design for a short list (3 to 6 items).

### Screen 7 — The plan, in words
- Purpose: the one part written by the AI. A short, warm coaching paragraph that
  ties the numbers together and explains the plan in plain language.
- This is the "soft voice" from section 3. It should read as prose, visually
  distinct from the number blocks. It can live at the top of the results as an
  intro, or as its own closing screen. The designer can decide placement.

> Note: screens 5, 6, and 7 together form "the results." They can be one
> scrolling results screen rather than three separate screens if that reads
> better on a phone. Treat them as three content blocks, one destination.

### Screen 8 — History
- Purpose: the reason accounts exist. Show the person's scans over time.
- Content: a reverse-chronological list of past scans. Each row shows the date
  plus two or three headline numbers (suggested: weight, percent body fat, daily
  energy target), and taps through to that scan's full stored results.
- **States to design:** the empty case (a brand-new account with no scans yet —
  this is the first thing most visitors will see, so it matters), one scan, and
  many scans.
- **Stretch:** a single small trend line (percent body fat over time) above the
  list. Design it, but assume it may ship later than the list.

### Screen 9 — Returning user / stale plan
- Purpose: what someone sees when they come back after a long gap.
- They land on their most recent plan, with its age clearly shown ("from your
  scan on 14 March"). Past 30 days it should read as **stale**: still valid as a
  record, but visibly due for a refresh, with a prominent "New scan" action.
- Design the age label and the stale treatment. Important: stale is not an error
  and not a warning. The old plan was correct when it was made and still is; it
  is just describing an older body.

## 6. Cross-cutting states to design

- **Loading:** the read step (screen 4) has a real wait while the model works.
  Design a loading state that holds attention rather than a plain spinner.
- **Error / fallback:** if reading or plan generation fails, the product falls
  back to a safe plain plan instead of showing a wrong number. Design a calm
  error state that does not feel broken.
- **Empty / uncertain data:** the flagged-field case in screen 4, and the
  no-imbalance case in screen 5.

## 7. Component inventory (what to design once, reuse everywhere)

- Number + label + unit pair (the core data primitive; appears everywhere)
- Big headline metric (the daily energy target)
- Choice controls: two-option toggle (sex, goal), five-option selector (activity)
- Sample-sheet thumbnail / picker
- Scan-reading animation and the extracted-value card
- Flagged/uncertain value treatment
- Imbalance line item
- Exercise row with type tag
- Prose / narrative block (the AI voice)
- Primary and secondary buttons, progress indication across the flow
- The phone frame the whole app sits inside on the page

## 8. Out of scope (do not design these)

- Coach / trainer mode: managing scans for other people. One account is one person.
- Editing or deleting a past scan or plan (scans are immutable — see section 3b)
- Settings screens, sharing, export
- Payment or subscription
- Onboarding tours beyond the simple intro
- Real-photo camera upload as a confirmed feature (leave a placeholder button
  only, per screen 3)

## 9. Open questions for the designer

1. Should screens 5 to 7 be one long scroll or a few swipes? Your call based on
   what reads best on a phone.
2. How literal should the "phone frame" be? A realistic device mockup, or a
   lighter suggestion of one?
3. Where does the AI-written paragraph belong: leading the results, or closing
   them?
4. How far do we push the scan-reading animation? It is the hero, so probably
   far, but it should still feel precise rather than gimmicky.

---

### One-line summary for context

InForm reads a gym body-scan and writes a trustworthy daily eating and training
plan. The design job is to make a short, phone-shaped web flow where the
scan-reading moment feels impressive and every number visibly traces back to the
scan it came from.
