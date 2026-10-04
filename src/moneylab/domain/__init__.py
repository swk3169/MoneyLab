"""Provider-neutral domain models. Nothing here may import a specific provider."""

from moneylab.domain.models import Market, Outcome

__all__ = ["Market", "Outcome"]
