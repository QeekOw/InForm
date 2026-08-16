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

## What this session verified vs. what it didn't

This pipeline (dataset generation, task-token setup, the training loop, and
checkpoint save/reload) is exercised end-to-end by
`tests/test_training.py`, but against a tiny public test-fixture model
(`optimum-internal-testing/tiny-random-VisionEncoderDecoderModel-donut`) and
a handful of sheets — not the real `donut-base` checkpoint or the full
~5,000-sheet set. That full run needs GPU compute this environment doesn't
have; it hasn't been executed, and no trained checkpoint exists yet. Issue
#8 (integrate into `extract_inbody` + score vs. the VLM baseline) is blocked
until someone runs this on GPU hardware and a real checkpoint exists.
