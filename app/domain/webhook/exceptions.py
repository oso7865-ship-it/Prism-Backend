class WebhookRejected(Exception):
    """Protocol rejection with a fixed, non-sensitive reason."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
