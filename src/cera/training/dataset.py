import argparse
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

from cera.synthetic import generate_sheet

TASK_TOKEN = "<s_inbody>"


def generate_dataset(output_dir: Path, n_per_device: int = 2500, seed_start: int = 0) -> None:
    """Render the full synthetic training set to disk (ADR-0007's ~5,000-sheet target).

    One PNG + one ground-truth JSON per sheet, seeded so the run is
    reproducible. Sequential and slow (~1s/sheet via headless-browser
    rendering — see cera.synthetic); the full 5,000-sheet set takes on the
    order of an hour.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = seed_start
    for device in ("inbody_270", "inbody_570"):
        for _ in range(n_per_device):
            # ponytail: one retry then skip, so a single flaky headless-browser
            # invocation (crash, transient hang) can't abort an hours-long batch.
            for attempt in range(2):
                try:
                    image_bytes, payload = generate_sheet(device, seed)
                    break
                except Exception as exc:
                    if attempt == 1:
                        print(f"Skipping {device} seed={seed} after 2 failed attempts: {exc}")
                        image_bytes = None
            if image_bytes is not None:
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
    args = parser.parse_args()
    generate_dataset(args.output_dir, n_per_device=args.n_per_device, seed_start=args.seed_start)


if __name__ == "__main__":
    _main()
