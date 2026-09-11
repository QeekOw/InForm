import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from inform import synthetic
from inform.synthetic import generate_sheet

# Generation (generate_dataset / the CLI) is torch-free — it only renders sheets.
# torch is needed solely by DonutInBodyDataset, so tolerate its absence and let
# the light (torch-free) venv generate datasets without pulling in torch.
try:
    import torch
    from torch.utils.data import Dataset
except ModuleNotFoundError:  # pragma: no cover - exercised only in the torch-free venv
    torch = None
    Dataset = object

TASK_TOKEN = "<s_inbody>"

# On-disk dataset format. generate_dataset writes DATASET_IMAGE_SUFFIX; readers
# accept any of IMAGE_SUFFIXES so that PNG sets written by earlier runs still
# load, and so a real phone photo (already .jpg) can be scored without being
# converted first. inform.evaluate deliberately duplicates IMAGE_SUFFIXES rather
# than importing it — that would make the light eval path depend on the training
# package — and tests/test_evaluate.py asserts the two never drift.
DATASET_IMAGE_SUFFIX = ".jpg"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")

_DEVICES = ("inbody_270", "inbody_570")

# What a dataset says about itself, written beside the sheets. A retrain is
# always a comparison between two datasets, and the v4 retrain could not be
# attributed partly because the link between a set on disk and the templates
# that rendered it lived only in prose and memory.
MANIFEST_GLOB = "dataset.*.json"


def manifest_name(seed_start: int, seed_end: int) -> str:
    """The manifest filename for one run, carrying its seed range.

    A 5,000-sheet run is sharded over disjoint seed ranges to parallelise, and
    the shards write into one directory. A single fixed filename would make
    them overwrite each other and leave the last shard's manifest describing
    the whole set, understating it. Naming each after its range means a
    directory holds one manifest per shard, all findable by `MANIFEST_GLOB`,
    and an unsharded run still leaves exactly one.
    """
    return f"dataset.{seed_start:06d}-{seed_end:06d}.json"


def fingerprint_inputs() -> list[Path]:
    """The files that decide what a rendered sheet looks like.

    The generator module and every device template. A change to any of them
    makes a different sheet out of the same (device, seed), which is exactly
    the change that must not go unnoticed across a retrain.

    Deliberately not covered: this module's own loop, which decides filenames
    and which seed goes to which device but not how a sheet renders, and the
    augmentation applied at training time rather than at generation.
    """
    generator = Path(synthetic.__file__)
    return [generator, *sorted((generator.parent / "templates").glob("*.html"))]


def generator_fingerprint() -> str:
    """sha256 over `fingerprint_inputs()`, path-tagged and in a fixed order.

    Paths are hashed alongside content so that renaming a template registers
    as a change; the sort keeps two shards of one run in agreement.
    """
    digest = hashlib.sha256()
    for path in fingerprint_inputs():
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_manifest(
    output_dir: Path, devices: tuple[str, ...], n_per_device: int, seed_start: int
) -> dict:
    """Record what rendered this set, and return the same dict.

    Seeds are reported as an inclusive range because that is the property a
    held-out set is defined by -- disjoint from the training set's -- so it
    should be checkable without recomputing it from the device count.
    """
    sheets = len(devices) * n_per_device
    manifest = {
        "devices": list(devices),
        "n_per_device": n_per_device,
        "sheets": sheets,
        "seed_start": seed_start,
        "seed_end": seed_start + sheets - 1,
        "generator_fingerprint": generator_fingerprint(),
    }
    name = manifest_name(manifest["seed_start"], manifest["seed_end"])
    (Path(output_dir) / name).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def generate_dataset(
    output_dir: Path,
    n_per_device: int = 2500,
    seed_start: int = 0,
    devices: tuple[str, ...] = _DEVICES,
) -> None:
    """Render a synthetic InBody dataset to disk (ADR-0007).

    One JPEG + one ground-truth JSON per sheet, seeded so the run is
    reproducible. Sequential and slow: ~5s/sheet via headless-browser
    rendering (measured at the A4 geometry; it was ~1s at the old near-square
    2.5x-smaller render), so a 2500-per-device run is ~7 hours. Shard it over
    disjoint `seed_start` ranges to parallelise — a sheet depends only on its
    device and seed, and the filename is `{device}_{seed:06d}`, so shards
    neither collide nor diverge from a single sequential run. Pass a single-element `devices` (e.g.
    `("inbody_270",)`) for a device-specific set — issue #13 retrains 270-only.
    Seeds run `seed_start .. seed_start + len(devices)*n_per_device - 1`; use a
    disjoint `seed_start` for a held-out set so it never overlaps the train set.

    Writes a manifest beside the sheets on completion (`manifest_name`),
    naming the devices, the seed range and `generator_fingerprint()`. Shards
    each write their own, so a sharded run leaves one per shard: they agree on
    the fingerprint and differ on the seed range.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = seed_start
    for device in devices:
        for _ in range(n_per_device):
            image_bytes, payload = generate_sheet(device, seed)
            stem = f"{device}_{seed:06d}"
            (output_dir / f"{stem}{DATASET_IMAGE_SUFFIX}").write_bytes(image_bytes)
            (output_dir / f"{stem}.json").write_text(payload.model_dump_json(), encoding="utf-8")
            seed += 1
    # Last, so a run killed part-way through leaves no manifest claiming a
    # sheet count it never rendered.
    write_manifest(output_dir, devices, n_per_device, seed_start)


class DonutInBodyDataset(Dataset):
    """Image -> target-JSON pairs for Donut fine-tuning, read from a
    generate_dataset() output directory.

    `processor` must already have TASK_TOKEN added as a special token (see
    train.build_model_and_processor) — its id is used as decoder_start_token.
    """

    def __init__(self, data_dir: Path, processor, max_target_length: int = 512) -> None:
        self._processor = processor
        self._max_target_length = max_target_length
        self._decoder_start_id = processor.tokenizer.convert_tokens_to_ids(TASK_TOKEN)
        self._samples = sorted(
            p for p in Path(data_dir).glob("*") if p.suffix.lower() in IMAGE_SUFFIXES
        )
        if not self._samples:
            raise ValueError(f"No .png sheets found in {data_dir}")

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, index: int) -> dict:
        image_path = self._samples[index]
        image = Image.open(image_path).convert("RGB")
        pixel_values = self._processor(image, return_tensors="pt").pixel_values.squeeze(0)

        ground_truth_json = image_path.with_suffix(".json").read_text(encoding="utf-8")
        target_text = TASK_TOKEN + ground_truth_json + self._processor.tokenizer.eos_token
        token_ids = self._processor.tokenizer(
            target_text,
            add_special_tokens=False,
            max_length=self._max_target_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).input_ids.squeeze(0)

        labels = token_ids.clone()
        labels[labels == self._processor.tokenizer.pad_token_id] = -100

        # Build decoder_input_ids explicitly (shift right by one, start
        # token first) instead of letting the model derive it from `labels`
        # — that derivation chokes on the -100 ignore-index used for padding.
        decoder_input_ids = torch.cat(
            [torch.tensor([self._decoder_start_id]), token_ids[:-1]]
        )

        return {"pixel_values": pixel_values, "labels": labels, "decoder_input_ids": decoder_input_ids}


def _main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic InBody training set.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--n-per-device", type=int, default=2500)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument(
        "--device", choices=_DEVICES, help="Generate only this device (default: both)."
    )
    args = parser.parse_args()
    devices = (args.device,) if args.device else _DEVICES
    generate_dataset(
        args.output_dir, n_per_device=args.n_per_device, seed_start=args.seed_start, devices=devices
    )


if __name__ == "__main__":
    _main()
