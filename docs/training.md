# Training the Donut engine

Phase 2 of ADR-0002: fine-tune Donut on the synthetic dataset from
`cera.synthetic.generate_sheet`, self-hosted per ADR-0005. This is offline
training infrastructure, not part of the `extract_inbody` runtime path —
install the extra separately:

```
pip install -e ".[dev,training]"
```

## 1. Generate the synthetic dataset

Paper target: ~5,000 sheets, ~2,500 each for InBody 270 and 570 (ADR-0007).
Rendering shells out to a headless Chrome/Edge per sheet (~1s/sheet), so the
full set takes on the order of an hour, sequentially, on a single machine.

```
python -m cera.training.dataset --output-dir data/synthetic --n-per-device 2500
```

Writes one `<device>_<seed>.png` + matching `.json` ground truth per sheet.

## 2. Fine-tune

```
python -m cera.training.train \
  --data-dir data/synthetic \
  --output-dir checkpoints/donut-inbody \
  --model-name-or-path naver-clova-ix/donut-base \
  --epochs 3 \
  --batch-size 2 \
  --learning-rate 3e-5
```

Needs a GPU in practice — `donut-base` fine-tuning on CPU is not
practical at this dataset size. Produces a checkpoint directory loadable via
`cera.training.train.load_checkpoint`.

## 3. Score Donut vs. the VLM baseline

Once a checkpoint exists, run the head-to-head on a held-out set of
`generate_dataset()` png/json pairs (ADR-0002 / ADR-0006):

```
python -m cera.compare \
  --data-dir data/holdout \
  --donut-checkpoint checkpoints/donut-inbody/checkpoint-1250
```

Both engines are scored through the full `extract_inbody` seam, so the
cross-check gate and fail-closed handling apply identically (a refusal counts
as a whole-sheet miss). Prints per-field, critical-field, and whole-sheet
accuracy side by side. Run once per ground-truth source (synthetic hold-out,
real hold-out) and report each separately — the synthetic→real gap is the
honest number. `--skip-vlm` scores Donut only (no OpenAI calls / cost).

To plug the fine-tuned engine into the production seam instead of the VLM
default: `extract_inbody(img, engine=donut.load_engine(checkpoint))`.

## What this session verified vs. what it didn't

This pipeline (dataset generation, task-token setup, the training loop, and
checkpoint save/reload) is exercised end-to-end by
`tests/test_training.py`, but against a tiny public test-fixture model
(`optimum-internal-testing/tiny-random-VisionEncoderDecoderModel-donut`) and
a handful of sheets — not the real `donut-base` checkpoint or the full
~5,000-sheet set. The real fine-tune has since been run on GPU (Colab T4); a
`donut-base` checkpoint exists. The `cera.compare` integration + scoring path
(step 3) is code-complete and unit-tested (`tests/test_donut.py`); the actual
head-to-head numbers come from running step 3 against that checkpoint on a
held-out set.
