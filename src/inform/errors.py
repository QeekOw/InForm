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
