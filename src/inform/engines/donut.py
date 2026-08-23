import json
from pathlib import Path

from pydantic import ValidationError

from inform.inbody import PartialInBody

# The task-prompt token the model was trained to emit first (see
# training.dataset.TASK_TOKEN) — duplicated as a plain string so parsing stays
# importable without torch/transformers (the training extra).
TASK_TOKEN = "<s_inbody>"

# The target the model emits is TASK_TOKEN + payload JSON + eos. Generation
# reverses that: decode, drop special tokens, JSON-parse into an InBodyPayload.
_MAX_NEW_TOKENS = 512


def load_engine(checkpoint_dir: Path):
    """Bind a fine-tuned Donut checkpoint into an extract_inbody-shaped engine.

    Returns a `Callable[[Path], PartialInBody]` — the same seam the VLM engine
    fills (ADR-0002) — with the (heavy) model loaded once and reused per call.
    Self-hosted: no cloud API (ADR-0005).
    """
    # Lazy: heavy deps (torch/transformers, the training extra) — kept out of
    # module import so the parsing logic below stays importable without them.
    import torch
    from PIL import Image

    from inform.training.train import load_checkpoint

    processor, model = load_checkpoint(Path(checkpoint_dir))
    model.eval()
    # Use the GPU when one is present — donut-base's 2560x1920 canvas is ~10-20x
    # faster on CUDA than CPU. Falls back to CPU transparently.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    def extract(image_path: Path) -> PartialInBody:
        image = Image.open(image_path).convert("RGB")
        pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)
        outputs = model.generate(
            pixel_values,
            max_new_tokens=_MAX_NEW_TOKENS,
            decoder_start_token_id=model.config.decoder_start_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            pad_token_id=processor.tokenizer.pad_token_id,
        )
        # skip_special_tokens drops eos/pad and TASK_TOKEN (an added special
        # token), leaving the raw JSON the model committed to.
        decoded = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        return _to_partial(decoded)

    return extract


def _to_partial(decoded: str) -> PartialInBody:
    # Donut has no "not an InBody sheet" signal (it only ever saw sheets in
    # training). Return whatever it read as a PartialInBody; the seam decides
    # floor-reject (nothing readable) vs partial (ADR-0008 amended). Never
    # fabricates: unparseable/invalid output yields an empty read (all None),
    # not a guessed value — the fail-closed guarantee is preserved.
    try:
        data = json.loads(decoded.replace(TASK_TOKEN, "").strip())
    except json.JSONDecodeError:
        return PartialInBody()
    if not isinstance(data, dict):
        return PartialInBody()
    try:
        return PartialInBody.model_validate(data)
    except ValidationError as exc:
        # Keep the keys that DID parse; drop only the invalid ones — a single
        # bad-typed field must not discard every other correct read (spec: "keep
        # whatever keys are present"). Never fabricates: dropped keys read unread.
        # A nested error (e.g. one bad segmental limb) drops the whole segmental
        # block, which then reads as unread — acceptable, still no guess.
        bad = {str(error["loc"][0]) for error in exc.errors()}
        return PartialInBody.model_validate({k: v for k, v in data.items() if k not in bad})
