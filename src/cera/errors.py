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
