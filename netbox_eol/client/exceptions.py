"""Exceptions for the eol.network client. Carry the contract error `code`."""


class EolApiError(Exception):
    def __init__(self, message, *, code=None, status=None):
        super().__init__(message)
        self.code = code
        self.status = status


class EolAuthError(EolApiError):
    """401/403 — invalid/missing key, inactive/unverified, or not an integration key."""


class EolRateLimited(EolApiError):
    """429 — minute limit or daily quota exhausted, still limited after retries."""
