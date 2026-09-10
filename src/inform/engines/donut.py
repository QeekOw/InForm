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
    body = decoded.replace(TASK_TOKEN, "").strip()
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = _salvage(body)
    if data is None:
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


def _salvage(body: str) -> dict | None:
    """Recover the fields a malformed generation already committed to.

    Donut stops mid-object often enough to matter: on the real-photo hold-out it
    emitted every field correctly and then ended before the closing brace, and
    discarding that read cost the whole sheet — every core field and the entire
    segmental lean block — over one missing character. The ValidationError branch
    in `_to_partial` above already keeps what parsed; this keeps the syntax-error
    path consistent with it.

    Cuts only ever fall on a **field boundary**, because every prefix of a number
    is itself a number: truncating `58.0` at `5` would parse cleanly and hand the
    caller a fabricated value, which is the one thing ADR-0008 forbids. Trailing
    content past the last boundary is dropped and reads unread. Returns None when
    nothing parses.
    """
    for cut, depth in _field_boundaries(body):
        try:
            data = json.loads(body[:cut] + "}" * depth)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _field_boundaries(body: str) -> list[tuple[int, int]]:
    """Every point the object can be truncated at without inventing a value.

    Yields `(cut, depth)` in preference order — longest read first — where `cut`
    slices `body` and `depth` is how many braces are still open there. A boundary
    is either the end of the whole body (only when it already ends on a closed
    string or object, never on a bare number) or a comma separating two members.
    """
    boundaries: list[tuple[int, int]] = []
    depth = in_string = escaped = 0
    last = ""
    commas: list[tuple[int, int]] = []
    for i, ch in enumerate(body):
        if in_string:
            if escaped:
                escaped = 0
            elif ch == "\\":
                escaped = 1
            elif ch == '"':
                in_string = 0
                last = '"'
            continue
        if ch == '"':
            in_string = 1
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            last = "}"
        elif ch == ",":
            commas.append((i, depth))
        if not ch.isspace() and ch not in '",{}':
            last = ch
    # A body ending on a closed string or object is complete up to its final
    # member; one ending on a digit may be a number cut in half, so it is not a
    # boundary at all and only the commas below are safe.
    if depth >= 1 and last in ('"', "}"):
        boundaries.append((len(body), depth))
    boundaries.extend((i, d) for i, d in reversed(commas) if d >= 1)
    return boundaries
