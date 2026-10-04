from __future__ import annotations

import logging

from rich.logging import RichHandler

from moneylab.core.redaction import RedactingFilter


def setup_logging(level: str = "INFO") -> None:
    handler = RichHandler(show_path=False, rich_tracebacks=False, markup=False)
    handler.addFilter(RedactingFilter())
    logging.basicConfig(level=level, format="%(message)s", handlers=[handler], force=True)
    # urllib3 retry chatter is noisy at INFO
    logging.getLogger("urllib3").setLevel(logging.WARNING)
