"""Hugging Face Space application entrypoint for InForm Donut OCR Engine.

Accepts an InBody sheet image and returns the extraction JSON containing
measured values, unread fields, and flagged cross-checks (ADR-0008 amended,
ADR-0010). Loads fine-tuned Donut weights from Hugging Face Hub. Never falls
back to cloud VLM (ADR-0005).
"""

import sys
from pathlib import Path
from typing import Any, Callable

# Support running directly from repo root or space directory
_repo_src = Path(__file__).resolve().parent.parent / "src"
if _repo_src.exists() and str(_repo_src) not in sys.path:
    sys.path.insert(0, str(_repo_src))

from inform.errors import MissingRequiredFieldsError, NotAnInBodySheetError
from inform.extract import Engine, default_engine, extract_inbody


def create_predict_fn(engine: Engine | None = None) -> Callable[[str | Path], dict[str, Any]]:
    """Create a prediction function backed by an extraction engine."""
    # Lazy default engine: Donut checkpoint is loaded once and cached.
    _engine: Engine | None = engine

    def predict(image_path: str | Path) -> dict[str, Any]:
        nonlocal _engine
        if _engine is None:
            _engine = default_engine()

        path = Path(image_path)
        try:
            extraction = extract_inbody(path, engine=_engine)
            return {
                "status": "complete",
                "data": extraction.data.model_dump(),
                "unread": extraction.unread,
                "flagged": extraction.flagged,
            }
        except NotAnInBodySheetError as exc:
            return {
                "status": "refused",
                "error": "not_an_inbody_sheet",
                "message": str(exc),
            }
        except MissingRequiredFieldsError as exc:
            return {
                "status": "refused",
                "error": "missing_required_fields",
                "unread": exc.fields,
                "message": str(exc),
            }

    return predict


def build_app(engine: Engine | None = None):
    """Build the Gradio interface for Hugging Face Space."""
    import gradio as gr

    predict_fn = create_predict_fn(engine=engine)

    def gradio_handler(image_file):
        if image_file is None:
            return {"status": "error", "message": "No image provided."}
        return predict_fn(image_file)

    demo = gr.Interface(
        fn=gradio_handler,
        inputs=gr.Image(type="filepath", label="InBody Sheet Photo"),
        outputs=gr.JSON(label="InBody Extraction"),
        title="InForm — Donut Engine (OCR)",
        description=(
            "Self-hosted Document Understanding Transformer (Donut) fine-tuned on "
            "InBody 270 and 570 result sheets. Outputs deterministic extracted data, "
            "unread fields, and flagged cross-checks. Never calls cloud VLM."
        ),
        api_name="predict",
        allow_flagging="never",
    )
    return demo


if __name__ == "__main__":
    demo = build_app()
    demo.launch(server_name="0.0.0.0", server_port=7860)
