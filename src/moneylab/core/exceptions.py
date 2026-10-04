"""Exception hierarchy. Callers above the provider layer only need ProviderError."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from moneylab.core.http import HttpDiagnostics


class MoneyLabError(Exception):
    """Base class for all MoneyLab errors."""


class NetworkError(MoneyLabError):
    """Request never produced an HTTP response (DNS, TLS, timeout, connection reset)."""


class ApiError(MoneyLabError):
    """An HTTP response was received but it was not usable (non-2xx or bad JSON)."""

    def __init__(self, message: str, diagnostics: HttpDiagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics

    @property
    def status_code(self) -> int | None:
        return self.diagnostics.status_code


class ProviderError(MoneyLabError):
    """A MarketDataProvider could not deliver data. Wraps Network/Api errors."""

    def __init__(self, provider: str, message: str, cause: Exception | None = None):
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.cause = cause

    @property
    def diagnostics(self) -> HttpDiagnostics | None:
        return getattr(self.cause, "diagnostics", None)
