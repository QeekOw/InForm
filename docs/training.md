# Training the Donut engine

Phase 2 of ADR-0002: fine-tune Donut on the synthetic dataset from
`inform.synthetic.generate_sheet`, self-hosted per ADR-0005. This is offline
training infrastructure, not part of the `extract_inbody` runtime path —
install the extra separately:

```
pip install -e ".[dev,training]"
```

## 1. Generate the synthetic dataset

Paper target: ~5,000 sheets, ~2,500 each for InBody 270 and 570 (ADR-0007).
Rendering shells out to a headless Chrome/Edge per sheet. Measured at the A4
geometry: **5.05s/sheet**, so ~7.6 hours for the full set sequentially. (It was
~1s/sheet before the sheet became A4-portrait at 2.5x device scale, which is
where the older "about an hour" figure came from.)

```
python -m inform.training.dataset --output-dir data/synthetic --n-per-device 2500
```

Writes one `<device>_<seed>.jpg` + matching `.json` ground truth per sheet.

**Shard it.** A sheet depends only on its device and seed, and the filename is
`{device}_{seed:06d}`, so disjoint `--seed-start` ranges produce byte-identical
output to one sequential run. Ten concurrent shards on 16 cores measured 0.635
sheets/s, cutting 7.6 hours to ~2. Seeds run continuously across devices within
one call, so a two-device 2500-each run covers 0-2499 (270) then 2500-4999 (570);
shard each device separately with `--device`:

```
python -m inform.training.dataset --output-dir <dir> --device inbody_270 --seed-start 0    --n-per-device 625
python -m inform.training.dataset --output-dir <dir> --device inbody_570 --seed-start 2500 --n-per-device 625
```

Use a disjoint `--seed-start` (e.g. 100000) for the held-out set so it never
overlaps the training set.

## 2. Fine-tune

```
python -m inform.training.train \
  --data-dir data/synthetic \
  --output-dir checkpoints/donut-inbody \
  --model-name-or-path naver-clova-ix/donut-base \
  --epochs 5 \
  --batch-size 1 \
  --dataloader-num-workers 4 \
  --learning-rate 3e-5
```

**Needs a 16GB GPU.** Measured at `--batch-size 1` with fp16 and gradient
checkpointing both on, torch reserves **15.64 GB**. The 16GB T4 on Colab or
Kaggle is what this config is sized for.

An 8GB card does not fail loudly, which is the trap. Under Windows WDDM the
driver oversubscribes GPU memory into host RAM over PCIe rather than raising
OOM, so training *runs*: 116s per optimizer step, about 29s per sheet, which
is **8.4 days** for a 5-epoch 5,000-sheet run. Measured on an RTX 4060 Laptop
8GB, at 100% GPU utilisation throughout, so utilisation is no signal here. If
a step takes two minutes, check `torch.cuda.max_memory_reserved()` against the
card's real capacity before looking anywhere else.

CPU-only is not an alternative at this dataset size. `--batch-size 2` OOMs
even on 16GB, so leave it at 1 and raise `--gradient-accumulation-steps`.

Produces a checkpoint directory loadable via
`inform.training.train.load_checkpoint`.

## 3. Score Donut vs. the VLM baseline

Once a checkpoint exists, run the head-to-head on a held-out set of
`generate_dataset()` png/json pairs (ADR-0002 / ADR-0006):

```
python -m inform.compare \
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
`donut-base` checkpoint exists. The `inform.compare` integration + scoring path
(step 3) is code-complete and unit-tested (`tests/test_donut.py`); the actual
head-to-head numbers come from running step 3 against that checkpoint on a
held-out set.
