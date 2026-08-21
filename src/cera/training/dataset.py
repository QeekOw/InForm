import argparse
from pathlib import Path

from PIL import Image

from cera.synthetic import generate_sheet

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

_DEVICES = ("inbody_270", "inbody_570")


def generate_dataset(
    output_dir: Path,
    n_per_device: int = 2500,
    seed_start: int = 0,
    devices: tuple[str, ...] = _DEVICES,
) -> None:
    """Render a synthetic InBody dataset to disk (ADR-0007).

    One PNG + one ground-truth JSON per sheet, seeded so the run is
    reproducible. Sequential and slow (~1s/sheet via headless-browser
    rendering — see cera.synthetic). Pass a single-element `devices` (e.g.
    `("inbody_270",)`) for a device-specific set — issue #13 retrains 270-only.
    Seeds run `seed_start .. seed_start + len(devices)*n_per_device - 1`; use a
    disjoint `seed_start` for a held-out set so it never overlaps the train set.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = seed_start
    for device in devices:
        for _ in range(n_per_device):
            image_bytes, payload = generate_sheet(device, seed)
            stem = f"{device}_{seed:06d}"
            (output_dir / f"{stem}.png").write_bytes(image_bytes)
            (output_dir / f"{stem}.json").write_text(payload.model_dump_json(), encoding="utf-8")
            seed += 1


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
        self._samples = sorted(Path(data_dir).glob("*.png"))
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
