class BegetError(Exception):
    """Base error for Beget API calls."""

    def __init__(self, message: str, code: str = "", details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        # MCP отдаёт наружу только str(exc): без кода агент видит голый текст
        # вроде "Failed to get DNS records" и не может отличить METHOD_FAILED
        # от INVALID_DATA, чтобы выбрать следующий шаг.
        return f"[{self.code}] {self.message}" if self.code else self.message


class BegetAuthError(BegetError):
    """Authentication failed — wrong login or password."""


class BegetAPIError(BegetError):
    """API returned an error response."""
