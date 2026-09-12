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
output to one sequential run. Seeds run continuously across devices within one
call, so a two-device 2500-each run covers 0-2499 (270) then 2500-4999 (570);
shard each device separately with `--device`:

```
python -m inform.training.dataset --output-dir <dir> --device inbody_270 --seed-start 0    --n-per-device 625
python -m inform.training.dataset --output-dir <dir> --device inbody_570 --seed-start 2500 --n-per-device 625
```

Use a disjoint `--seed-start` (e.g. 100000) for the held-out set so it never
overlaps the training set.

**Shard by equal sheet count, not by how fast a device renders.** Measured on the
v5 run (5,000 sheets, 16 cores): six concurrent shards gave **0.611 sheets/s**
aggregate, against 0.635 for ten shards on an earlier run — throughput saturates
well before ten, so a handful is enough and more shards mostly add contention.

The v5 run split 2-way on the 270 (1250 each) and 4-way on the 570 (625 each),
reasoning that a 570 renders in ~3.8s against the 270's ~1.8s measured *solo*.
That was wrong: under contention the per-sheet cost converges, so the 270 shards
finished in 136 min and the 570 shards in 99, and the 270 half was the long pole
by half an hour. Equal sheet counts per shard would have finished in ~90 min.
Solo render times do not predict sharded wall clock.

**Each shard writes its own manifest.** `dataset.{seed_start}-{seed_end}.json`,
naming the devices, the inclusive seed range and a fingerprint over the generator
module and every device template (`inform.training.dataset.manifest_name`). A
retrain is a comparison between two datasets, so before believing any comparison,
check the fingerprints agree across a set's shards and match the commit you
trained. It is what caught the 570 sheets changing under the 270 fat-figure fix
(ADR-0007, 2026-09-11 amendment).


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

## 4. Read the retrain against the real hold-out

`inform.compare` (step 3) answers "Donut or the VLM". A retrain asks a different
question — "is this checkpoint better than the one we ship" — and that is
`inform.holdout`, scored against the hand-labelled real photos (ADR-0006).

`--reads` and `--donut-checkpoint` are both repeatable, and mixing them is the
usual case: a new checkpoint against recorded baselines. More than one source
prints the comparison table instead of the single-engine report.

```
python -m inform.holdout \
  --data-dir data/real_holdout --labels data/real_holdout/labels.json \
  --reads data/real_holdout/probe-donut-both-v3-reads.json \
  --donut-checkpoint D:/cera/kaggle_out_v5/donut-both-v5/checkpoint-3750
```

Recorded reads for the shipped baselines live beside the images (gitignored), so
a baseline costs no GPU and no re-inference. That is what keeps a published
number checkable after the checkpoint it came from has moved on.

**Read the silent-error rate beside the outcome split, never alone.** An engine
that flags or under-reads every sheet has no `unverified` reads and therefore a
perfect headline. The table prints both together for that reason; CONTEXT.md
states the rule.

**Per-epoch checkpoint dirs may carry no processor.** `save_pretrained` runs once
after `trainer.train()` returns, so the processor lands at the run root and not
in `checkpoint-N/`. Load the model from the checkpoint and the processor from the
root. Its presence at the root is also the cheapest evidence a run finished
rather than being cut off by a wall-clock cap.

**Score every engine on identically preprocessed images.** Cropping the hold-out
photos to the sheet changes which checkpoint wins (#53) without touching any
checkpoint, so a comparison is only meaningful when both sides got the same
picture. Say which in whatever you write down.

**Two runs both name a checkpoint `checkpoint-3750`.** The table labels a column
by the shortest path suffix that separates it from the others, so comparing the
same epoch across runs prints `donut-both-v4/checkpoint-3750` against
`donut-both-v5/checkpoint-3750` rather than silently scoring one and showing the
other.

### Measured: what the hold-out says depends on how the photo is framed

Both retrains since v3 have been scored this way, over 12 real sheets of which 6
are hand-labelled. That is 66 labelled field observations, 36 core and 30
segmental.

Score them on the hold-out photos as they come off the phone, and v3 wins
everything:

| uncropped | v3 | v4-e3750 | v5-e3750 |
|---|---|---|---|
| core fields | **33/36** | 30/36 | 28/36 |
| segmental lean | **23/30** | 20/30 | 15/30 |
| critical (LBM + limbs) | **26/36** | **26/36** | 21/36 |
| `percent_body_fat` | **6/6** | 3/6 | 1/6 |
| `segmental_lean.right_arm_kg` | 1/6 | **2/6** | 1/6 |

Crop each photo to the sheet first (#53) and the ranking changes:

| cropped to the sheet | v3 | v4-e3750 | v5-e3750 |
|---|---|---|---|
| core fields | **36/36** | 28/36 | 31/36 |
| segmental lean | 27/30 | 22/30 | **28/30** |
| critical (LBM + limbs) | 33/36 | 27/36 | **34/36** |
| `percent_body_fat` | **6/6** | 2/6 | 1/6 |
| `segmental_lean.right_arm_kg` | 4/6 | 3/6 | **5/6** |

**Read the two tables together or neither.** Uncropped, v5 looks like a failed
retrain that gave up eight segmental observations. Cropped, v5 has the best
segmental lean and the best critical-field score of any engine we have, and its
`right_arm_kg` (the field the whole 270 Segmental Fat fix targeted) goes 1/6 to
5/6. The fix worked. The uncropped hold-out could not see it, because the
framing mismatch was costing more accuracy than the fix was buying.

`percent_body_fat` is the exception and survives cropping untouched: 1/6 either
way, against v3's 6/6. That is now v5's only real deficit and it is #52.

**v3 stays the default checkpoint** (ADR-0010, 2026-09-12 amendment) because it
is the only engine that reads every core field, and the five observations it
wins on `percent_body_fat` outweigh the two v5 wins elsewhere. That is a
narrower margin than the uncropped numbers suggest, and it turns on one field.

**The resolution here is a real constraint** (#24). A three-field swing is
comfortably visible at 66 observations, so the cropping result is safe. A
one-field margin between v3 and v5 is not, and neither is a silent-error
denominator of one to three: v5-e3750 leaves four of its five `unverified`
sheets unlabellable, a blind spot larger than the measurement it reports.
Labelling the remaining six sheets is what would let this table settle the
narrow comparisons it currently only gestures at.

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
