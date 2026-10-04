"""Service layer for the Financial Memory Engine.

Other Django apps should import from here rather than reaching into the
models directly.  This keeps business logic in one place and makes it easy
to swap the underlying store later.
"""
from .memory_service import (  # noqa: F401
    MemoryService,
    memory_service,
    ClassificationResult,
    normalise_signal,
)
from .recurring_detector import RecurringDetector  # noqa: F401
