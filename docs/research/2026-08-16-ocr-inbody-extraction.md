# OCR / extraction approach for Module 1 (InBody sheet → `InBodyPayload`)

_Research date: 2026-08-16. Scope: how to extract labeled numeric fields from a
photographed/scanned InBody body-composition result sheet into the fixed
`InBodyPayload` schema (weight, LBM, SMM, PBF, BMR, visceral fat level, and a
5-field segmental-lean object)._

Every non-obvious claim below is cited inline to a primary source (official
docs, model cards, source repos, papers, first-party pricing). Where I could
not verify something from a primary source, or where sources disagree, that is
called out explicitly.

---

## Summary & recommendation

**Recommended path for a small student team with no large real dataset and a
fixed output schema: use a general-purpose vision-language model (VLM) with
guaranteed structured/JSON-schema output in a zero/few-shot configuration —
not a fine-tuned Donut — for the first working version.**

Reasoning in brief:

- **Donut is a fine-tune-first model.** Its own HuggingFace model card states
  `donut-base` "is meant to be fine-tuned on a downstream task" and is not
  useful standalone ([model card](https://huggingface.co/naver-clova-ix/donut-base)).
  There is no released Donut checkpoint for InBody sheets, so choosing Donut
  means building a labeled image→JSON dataset and running a GPU fine-tune — the
  Donut base model itself was trained on 64 A100 GPUs, and even the CORD
  fine-tune example assumes an A100 ([Donut repo](https://github.com/clovaai/donut)).
  Real InBody sheets are scarce and privacy-sensitive, so the training data
  does not exist for the team today.
- **A schema-constrained VLM removes the training step entirely.** OpenAI
  Structured Outputs *guarantees* the model's response conforms to a supplied
  JSON Schema and is compatible with vision inputs, so the model can be pointed
  at a photo and told to emit exactly `InBodyPayload`
  ([OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/),
  [guide](https://platform.openai.com/docs/guides/structured-outputs)).
  Open-weight VLMs (Qwen2.5-VL) advertise the same document-extraction-to-JSON
  use case and can be schema-constrained locally
  ([Qwen2.5-VL blog](https://qwenlm.github.io/blog/qwen2.5-vl/)).
- **The task is small and fixed** (~11 scalar fields on a fixed-layout printout),
  which is exactly where a strong VLM with a schema shines and where the cost of
  standing up a training pipeline is hard to justify.

**What would change the recommendation toward fine-tuning Donut (or a
layout-aware model):** (a) the team accumulates a few hundred–thousand labeled
real InBody images and can render realistic synthetic ones with known
ground-truth (Donut's own SynthDoG approach shows this is viable —
[Donut paper §SynthDoG](https://arxiv.org/abs/2111.15664)); (b) per-call API
cost or sending user body-composition images to a third-party API becomes a
privacy/cost blocker, pushing toward a self-hosted model; or (c) measured
accuracy of the zero-shot VLM on the numeric fields is inadequate. The
pragmatic plan is therefore: **ship the VLM+schema path now, log real sheets
(with consent) to build a dataset, and keep Donut/self-hosted VLM fine-tuning
as a phase-2 option once data exists.**

---

## Q1 — Is Donut a sensible choice for this task?

**What Donut is.** Donut ("Document Understanding Transformer") is an OCR-free
Visual Document Understanding model introduced in *OCR-free Document
Understanding Transformer* (Kim et al., ECCV 2022,
[arXiv:2111.15664](https://arxiv.org/abs/2111.15664)). Instead of running OCR
and then parsing its text, Donut maps a document **image directly to a
structured output sequence**. The paper motivates this by citing the drawbacks
of OCR-based pipelines: "high computational costs for using OCR, inflexibility
of OCR models on languages or types of documents, and OCR error propagation to
the subsequent process" ([abstract](https://arxiv.org/abs/2111.15664)).

**Architecture.** Per the model card, "Donut consists of a vision encoder
(Swin Transformer) and a text decoder (BART)"; the encoder turns the image into
embeddings and the BART decoder autoregressively generates the output tokens
([donut-base model card](https://huggingface.co/naver-clova-ix/donut-base)).

**What tasks it is designed for.** The official implementation lists the tasks
Donut was built and evaluated for: **document parsing / information extraction
(CORD receipts)**, **document classification (RVL-CDIP)**, **document VQA
(DocVQA Task 1)**, and **train-ticket parsing** (reported at 98.7% accuracy)
([Donut GitHub](https://github.com/clovaai/donut)). CORD is a *receipt parsing*
dataset — semi-structured printed documents with labeled fields and numeric
values — which is the closest public analogue to an InBody sheet. So the task
family (extract labeled fields incl. numbers from a semi-structured printout
into JSON) is squarely what Donut was designed for. That makes Donut
**architecturally a sensible fit** for the InBody problem.

**The catch — it must be fine-tuned.** The base model card is explicit:
`donut-base` "is meant to be fine-tuned on a downstream task, like document
image classification or document parsing"; the base checkpoint has "limited
practical application" on its own
([donut-base model card](https://huggingface.co/naver-clova-ix/donut-base)).
The receipt-parsing behavior lives in the *fine-tuned* `donut-base-finetuned-cord-v2`
checkpoint, not the base one
([CORD-v2 card](https://huggingface.co/naver-clova-ix/donut-base-finetuned-cord-v2)).
There is no public InBody-fine-tuned Donut, so using Donut here means creating
a dataset and fine-tuning.

**Training data format (image → JSON).** Fine-tuning expects a dataset
directory with a `metadata.jsonl` file, one line per image, of the form
([Donut GitHub](https://github.com/clovaai/donut)):

```
{"file_name": "<image_path>", "ground_truth": "<json-stringified dict>"}
```

For information extraction the `ground_truth` string wraps a `gt_parse` object
holding the structured fields, e.g. CORD uses
`{"gt_parse": {"menu": [{"nm": "ICE BLACKCOFFEE", "cnt": "2", ...}], ...}}`
([Donut GitHub](https://github.com/clovaai/donut)). For our case the `gt_parse`
would be the `InBodyPayload` JSON (weight_kg, lean_body_mass_kg, …, and the
nested SegmentalLean object). Donut learns the field names and nesting from
examples; the schema is taught by data, not declared.

**GPU / scale.** The base model was pre-trained on "64 A100 GPUs (~2.5 days)"
over IIT-CDIP (11M) + SynthDoG data; fine-tuning examples in the repo assume "a
single NVIDIA A100 GPU" ([Donut GitHub](https://github.com/clovaai/donut)). The
repo does **not** state a hard minimum labeled-example count for a downstream
fine-tune (unverified — treat as "needs experimentation"), but a non-trivial
labeled set plus GPU time is required either way.

> Bottom line for Q1: Donut is a *good architectural match* for InBody-sheet
> extraction, but only as a fine-tuned model. Its cost is the data + GPU it
> demands, which is exactly what this project lacks up front.

---

## Q2 — Alternatives worth comparing

### (a) Vision-language models with structured/JSON output

**OpenAI vision + Structured Outputs.** OpenAI's Structured Outputs feature
"ensure[s] model-generated outputs will exactly match JSON Schemas provided by
developers," is generally available on function-calling-capable models
(gpt-4o, gpt-4o-mini), and "Structured Outputs with function calling is …
compatible with vision inputs"
([OpenAI announcement](https://openai.com/index/introducing-structured-outputs-in-the-api/),
[Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs)).
The SDKs let you define the schema directly with a Pydantic model — which maps
cleanly onto an existing `InBodyPayload` dataclass/Pydantic model.
- *Strengths for this task:* no training; the schema (including the nested
  SegmentalLean object and integer visceral-fat level) is *guaranteed* to be
  respected; strong general reading of numbers and labels on a fixed-layout
  printout; fastest path to a working extractor.
- *Weaknesses:* per-call cost; sends user body-composition images to a
  third-party API (privacy/compliance consideration for health data); accuracy
  on decimals must still be validated (see Q4 verification note).

**Qwen2.5-VL (open weights).** The Qwen team states Qwen2.5-VL "supports
structured outputs for data like scans of invoices, forms, tables" and can
produce "stable JSON output for … attributes"
([Qwen2.5-VL blog](https://qwenlm.github.io/blog/qwen2.5-vl/)); the 7B Instruct
model is on HuggingFace ([Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)).
JSON conformance can be enforced with constrained decoding (e.g. the `outlines`
library / a Pydantic schema), as noted in the model's own HF discussion.
- *Strengths:* self-hostable (keeps health images in-house), no per-call API
  fee, same "image → JSON fields" capability as the closed VLMs, fits the
  optional heavy-ML dependency group (torch/transformers) already planned.
- *Weaknesses:* needs a GPU to run at reasonable latency; JSON-schema adherence
  is enforced via extra tooling rather than a first-party guarantee; check the
  specific checkpoint's license terms before shipping (the Qwen2.5-VL cards on
  HF should be read for the exact license — treat as unverified here).

### (b) Layout-aware OCR / Document AI

**LayoutLMv3 (Microsoft).** A multimodal Transformer for Document AI that can be
"fine-tuned for … form understanding, receipt understanding, and document
visual question answering"
([HF docs](https://huggingface.co/docs/transformers/model_doc/layoutlmv3)).
- *Strengths:* strong on fixed-layout forms; uses text+layout+image.
- *Weaknesses:* still needs OCR boxes as input and task-specific fine-tuning
  (more moving parts than Donut). **Licensing blocker:** the HF weights are
  released under **CC BY-NC-SA 4.0 (non-commercial)**
  ([microsoft/layoutlmv3-large](https://huggingface.co/microsoft/layoutlmv3-large)),
  which restricts commercial use — a real constraint if CERA is ever
  commercialized.

**Azure AI Document Intelligence (custom extraction).** Managed cloud service;
custom extraction is billed at **$30 per 1,000 pages**, custom neural training
is free for the first 10 hours/month then $3/hour
([Azure pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/)).
- *Strengths:* purpose-built for "extract labeled fields from a fixed-layout
  form"; you label a handful of sample layouts rather than writing training
  code; robust to photo/scan noise.
- *Weaknesses:* cloud dependency + per-page cost + sending health images to a
  third party; still requires labeling sample sheets.

**AWS Textract.** `AnalyzeExpense` targets invoices/receipts; the general-
purpose **Queries** feature lets you ask for specific fields. Queries are
priced around **$15 per 1,000 pages** and custom queries $25/1,000 pages
([Textract pricing](https://aws.amazon.com/textract/pricing/)).
- *Strengths:* "Queries" maps well to "give me these ~11 named values"; no model
  training.
- *Weaknesses:* returns text answers you must still coerce into the typed schema;
  cloud + per-page cost + third-party health data.

**Google Document AI (Form Parser / Custom Extractor).** Both Form Parser and
Custom Extractor are **$30 per 1,000 pages** (dropping to $20 at very high
volume); the generative-AI Custom Extractor can be created "without the need to
label, annotate, or train"
([Google Document AI](https://cloud.google.com/document-ai),
[Form Parser docs](https://cloud.google.com/document-ai/docs/form-parser)).
- *Strengths:* form/key-value extraction is the core product; low-setup custom
  extractor.
- *Weaknesses:* same cloud + cost + third-party health-data trade-offs.

**PaddleOCR / PP-StructureV3 / PP-ChatOCRv4 (open source).** Apache-2.0
licensed toolkit; PP-StructureV3 does layout + table + structure extraction to
JSON/Markdown, and PP-ChatOCRv4 pairs OCR with an LLM for key-information
extraction
([PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR),
[PaddleOCR 3.0 report](https://arxiv.org/pdf/2507.05595)).
- *Strengths:* permissive license, self-hostable, no per-call fee, strong
  multilingual OCR.
- *Weaknesses:* more assembly (OCR → structure → your parsing/mapping layer);
  the KIE quality depends on the paired LLM.

### (c) Plain OCR + a parsing layer

**Tesseract (Apache-2.0) and EasyOCR.** Tesseract is the long-standing
open-source LSTM OCR engine ([Tesseract GitHub](https://github.com/tesseract-ocr/tesseract),
[docs](https://tesseract-ocr.github.io/)). You would run OCR, then write rules
(regex/anchor-on-label) to pull each numeric field.
- *Strengths:* free, fully local (best privacy), simple for a truly fixed layout.
- *Weaknesses:* brittle to photo skew/lighting; and specifically weak on the
  numbers that matter here — Tesseract's own accuracy guidance notes it is
  tuned for prose rather than "receipts, price lists, or codes"
  ([ImproveQuality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)),
  and comparative testing reports digit-level errors (e.g. dropping a digit in
  `29977.23`) — meaning a hand-written parsing layer bears all the burden of
  correctness. (That specific digit-error example is from a secondary comparison
  blog, so treat the exact figure as indicative, not authoritative.)

**Summary table (fitness for "labeled numeric fields on a fixed-layout
medical/fitness printout"):**

| Option | Training needed? | Schema guarantee | Data privacy | Cost model | License note |
|---|---|---|---|---|---|
| Donut (fine-tuned) | Yes (image→JSON + GPU) | Learned, not guaranteed | Self-host ✔ | Compute only | MIT (base) |
| OpenAI VLM + Structured Outputs | No | **Guaranteed to schema** | 3rd-party API ✖ | Per call | Proprietary API |
| Qwen2.5-VL | No (few/zero-shot) | Via constrained decoding | Self-host ✔ | Compute only | Check card |
| LayoutLMv3 | Yes | No | Self-host ✔ | Compute only | **CC BY-NC (non-commercial)** |
| Azure Doc Intelligence | Light (label samples) | Field-typed | 3rd-party ✖ | $30/1k pages | Proprietary |
| AWS Textract Queries | No | Text answers → coerce | 3rd-party ✖ | ~$15/1k pages | Proprietary |
| Google Document AI | No/light | Field-typed | 3rd-party ✖ | $30/1k pages | Proprietary |
| PaddleOCR (PP-Structure/ChatOCR) | No/light | Via LLM layer | Self-host ✔ | Compute only | Apache-2.0 |
| Tesseract/EasyOCR + rules | No (write rules) | You enforce | Self-host ✔ | Compute only | Apache-2.0 |

---

## Q3 — Training / fine-tuning data options

Real InBody sheets are scarce and privacy-sensitive, so the realistic options
are:

**1. Synthetic data generation (strong precedent from Donut itself).** Donut's
authors faced the same "no large real dataset" problem and solved it with
**SynthDoG (Synthetic Document Generator)**: they render synthetic document
images to pre-train the model so it is "flexible on various languages and
domains," and release SynthDoG data (0.5M samples each for English, Chinese,
Japanese, Korean) plus generation code
([Donut GitHub](https://github.com/clovaai/donut),
[Donut paper](https://arxiv.org/abs/2111.15664)). For CERA this means:
programmatically render realistic InBody-style sheets (fixed template, varied
fonts/values/segmental figures) with the ground-truth `InBodyPayload` known by
construction — you get perfectly-labeled image→JSON pairs for free and no real
patient data. This is the single most defensible way to build a Donut (or
Qwen) fine-tuning set here, because the label is generated alongside the image.

**2. Data augmentation.** Apply photo-realistic perturbations to synthetic (or
the few real) sheets — skew, rotation, blur, lighting, JPEG noise, perspective
— so the model generalizes from clean renders to phone photos. (General ML
practice; combine with SynthDoG-style rendering above.)

**3. Few-shot / zero-shot with a VLM (avoid training entirely).** Because the
output schema is fixed and small, a schema-constrained VLM can extract the
fields with zero or a handful of in-prompt examples, sidestepping dataset
construction altogether — this is the whole premise of the Q4 recommendation
([OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/),
[Qwen2.5-VL](https://qwenlm.github.io/blog/qwen2.5-vl/)).

A pragmatic hybrid: start zero-shot with a VLM; simultaneously stand up a
SynthDoG-style renderer so that if/when you want a self-hosted fine-tune, the
labeled data already exists. Real sheets, collected with user consent, become
a small high-value evaluation/holdout set.

---

## Q4 — Recommendation

**Recommended: a schema-constrained VLM in zero/few-shot mode as the Module 1
extractor for v1.** Concretely, send the sheet image to a VLM and require the
`InBodyPayload` JSON Schema as the output contract — OpenAI Structured Outputs
if a hosted API is acceptable (guaranteed schema conformance, incl. the nested
SegmentalLean object and the integer visceral-fat level), or Qwen2.5-VL with
constrained decoding if the team wants everything self-hosted for health-data
privacy.

**Why this over fine-tuning Donut, for this team, now:**

- **No dataset exists.** Donut needs labeled image→JSON pairs and a GPU; the
  base card says it "is meant to be fine-tuned" and isn't usable as-is
  ([donut-base](https://huggingface.co/naver-clova-ix/donut-base)). Real InBody
  data is scarce/sensitive. The VLM path needs zero training data to start.
- **The schema is fixed and small.** Structured Outputs *guarantees* conformance
  to that schema
  ([OpenAI](https://openai.com/index/introducing-structured-outputs-in-the-api/)),
  removing a whole class of parsing/format bugs — you get typed fields, not
  free text to post-process.
- **Speed to a working module.** Zero training pipeline, no GPU procurement,
  fits a small student team's time budget; the heavy-ML dependency group
  (torch/transformers) stays optional for the hosted-API route and is only
  pulled in if you self-host Qwen.

**What would change the recommendation:**

- **Enough labeled data appears.** If you build a SynthDoG-style renderer (Donut
  precedent, [paper](https://arxiv.org/abs/2111.15664)) or collect a few
  hundred+ consented real sheets, fine-tuning Donut (MIT-licensed, self-hosted,
  no per-call fee) becomes attractive — especially to eliminate ongoing API
  cost and to keep health images in-house.
- **Privacy/cost blocks the hosted API.** Body-composition images are health
  data; if sending them to a third-party API is unacceptable, prefer the
  self-hosted Qwen2.5-VL route immediately, and consider Donut fine-tuning once
  data exists. (Avoid LayoutLMv3 for a commercial product given its
  **non-commercial CC BY-NC-SA license**,
  [card](https://huggingface.co/microsoft/layoutlmv3-large).)
- **VLM accuracy on numbers proves inadequate.** Decimal fields (e.g. 34.2 kg
  SMM) must be validated on real photos; if the zero-shot VLM misreads
  decimals/segmental values, move to a fine-tuned model trained on
  synthetic+augmented data, or add a managed form service (Azure/Google/AWS)
  as a fallback. **This numeric accuracy has not been verified here and must be
  measured on real InBody photos before shipping.**

**Explicitly unverified / caveats:**
- No primary-source benchmark of any of these models *on InBody sheets
  specifically* exists (none found); all fitness claims are by analogy to
  receipt/form parsing.
- Donut's minimum labeled-example count for a good downstream fine-tune is not
  stated in its repo.
- The exact license of the specific Qwen2.5-VL checkpoint you deploy should be
  read from its model card before commercial use.
- The Tesseract digit-error example comes from a secondary comparison blog, not
  a primary benchmark.

---

## Sources

**Donut (primary):**
- Kim et al., *OCR-free Document Understanding Transformer* (ECCV 2022) — https://arxiv.org/abs/2111.15664
- Official implementation + SynthDoG + dataset format — https://github.com/clovaai/donut
- `naver-clova-ix/donut-base` model card — https://huggingface.co/naver-clova-ix/donut-base
- `naver-clova-ix/donut-base-finetuned-cord-v2` model card — https://huggingface.co/naver-clova-ix/donut-base-finetuned-cord-v2

**VLMs with structured output:**
- OpenAI, *Introducing Structured Outputs in the API* — https://openai.com/index/introducing-structured-outputs-in-the-api/
- OpenAI Structured Outputs guide — https://platform.openai.com/docs/guides/structured-outputs
- Qwen2.5-VL blog — https://qwenlm.github.io/blog/qwen2.5-vl/
- `Qwen/Qwen2.5-VL-7B-Instruct` model card — https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct

**Layout-aware / Document AI:**
- LayoutLMv3 (Transformers docs) — https://huggingface.co/docs/transformers/model_doc/layoutlmv3
- `microsoft/layoutlmv3-large` (license: CC BY-NC-SA 4.0) — https://huggingface.co/microsoft/layoutlmv3-large
- Azure AI Document Intelligence pricing — https://azure.microsoft.com/en-us/pricing/details/document-intelligence/
- AWS Textract pricing — https://aws.amazon.com/textract/pricing/
- Google Cloud Document AI — https://cloud.google.com/document-ai
- Google Document AI Form Parser docs — https://cloud.google.com/document-ai/docs/form-parser

**Open-source OCR:**
- PaddleOCR — https://github.com/PaddlePaddle/PaddleOCR
- PaddleOCR 3.0 Technical Report — https://arxiv.org/pdf/2507.05595
- Tesseract OCR engine — https://github.com/tesseract-ocr/tesseract
- Tesseract docs / ImproveQuality — https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
