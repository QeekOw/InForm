from pathlib import Path


class InBodyExtractionError(Exception):
    """Fail-closed error: extract_inbody refuses rather than fabricates a value."""


class NotAnInBodySheetError(InBodyExtractionError):
    def __init__(self) -> None:
        super().__init__(
            "This image does not appear to be an InBody result sheet. "
            "Please upload a clear photo of your InBody 270 or 570 sheet."
        )


class MissingRequiredFieldsError(InBodyExtractionError):
    def __init__(self, fields: list[str]) -> None:
        self.fields = fields
        super().__init__(
            "Could not confidently read: " + ", ".join(fields) + ". "
            "Please re-upload a clearer photo."
        )


class DonutCheckpointError(Exception):
    """The default Donut engine could not be loaded (ADR-0010).

    Deliberately NOT an InBodyExtractionError: a missing checkpoint is an
    operational/config fault, not a fail-closed *read* refusal, so evaluate.py
    must not swallow it as an all-wrong sheet. Raised instead of silently
    falling back to the cloud VLM, which would ship real health data to a
    third party the caller believes is self-hosted (ADR-0005)."""

    def __init__(self, checkpoint: str | Path, *, missing_training_extra: bool = False) -> None:
        self.checkpoint = checkpoint
        remedy = (
            "Install the training extra: pip install -e \".[training]\"."
            if missing_training_extra
            else (
                f"Download the checkpoint to {checkpoint} (e.g. "
                "`kaggle kernels output qeekowen/cera-combined-test -p ./models/donut-both-v3`), "
                "or point INFORM_DONUT_CKPT at the checkpoint dir."
            )
        )
        super().__init__(
            f"Could not load the default Donut engine from {checkpoint!r}. {remedy} "
            "Refusing to fall back to the cloud VLM (ADR-0005: no real PHI to the cloud)."
        )


class IncompleteExtractionError(Exception):
    """Fail-closed error: run_pipeline refuses to build a plan from an
    InBodyExtraction that has unread or flagged fields, rather than filling
    gaps or ignoring a cross-check flag."""

    def __init__(self, unread: list[str], flagged: list[str]) -> None:
        self.unread = unread
        self.flagged = flagged
        super().__init__(
            f"Cannot build a plan from an incomplete extraction. "
            f"Unread: {unread or 'none'}; flagged for review: {flagged or 'none'}."
        )
