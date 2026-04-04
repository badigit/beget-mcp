class BegetError(Exception):
    """Base error for Beget API calls."""

    def __init__(self, message: str, code: str = "", details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class BegetAuthError(BegetError):
    """Authentication failed — wrong login or password."""


class BegetAPIError(BegetError):
    """API returned an error response."""
