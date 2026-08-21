import json
from pathlib import Path

from pydantic import ValidationError

from cera.errors import MissingRequiredFieldsError
from cera.inbody import InBodyPayload

# The task-prompt token the model was trained to emit first (see
# training.dataset.TASK_TOKEN) — duplicated as a plain string so parsing stays
# importable without torch/transformers (the training extra).
TASK_TOKEN = "<s_inbody>"

# The target the model emits is TASK_TOKEN + payload JSON + eos. Generation
# reverses that: decode, drop special tokens, JSON-parse into an InBodyPayload.
_MAX_NEW_TOKENS = 512


def load_engine(checkpoint_dir: Path):
    """Bind a fine-tuned Donut checkpoint into an extract_inbody-shaped engine.

    Returns a `Callable[[Path], InBodyPayload]` — the same seam the VLM engine
    fills (ADR-0002) — with the (heavy) model loaded once and reused per call.
    Self-hosted: no cloud API (ADR-0005).
    """
    # Lazy: heavy deps (torch/transformers, the training extra) — kept out of
    # module import so the parsing logic below stays importable without them.
    from PIL import Image

    from cera.training.train import load_checkpoint

    processor, model = load_checkpoint(Path(checkpoint_dir))
    model.eval()

    def extract(image_path: Path) -> InBodyPayload:
        image = Image.open(image_path).convert("RGB")
        pixel_values = processor(image, return_tensors="pt").pixel_values
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
        return _to_payload(decoded)

    return extract


def _to_payload(decoded: str) -> InBodyPayload:
    # Donut has no "not an InBody sheet" signal (it only ever saw sheets in
    # training), so a garbled/incomplete generation is a misread, not a
    # rejection: fail closed on the required fields rather than fabricate.
    try:
        data = json.loads(decoded.replace(TASK_TOKEN, "").strip())
    except json.JSONDecodeError:
        data = {}
    try:
        return InBodyPayload.model_validate(data)
    except ValidationError as exc:
        raise MissingRequiredFieldsError(_missing_fields(exc)) from exc


def _missing_fields(exc: ValidationError) -> list[str]:
    return [".".join(str(part) for part in error["loc"]) for error in exc.errors()]
