# path: umbra/__init__.py

"""
Umbra – Subconscious / Reflex Layer

This package is already implemented on Satcha's side.

Here we simply expose a canonical `get_umbra_engine()` function
that returns an object implementing `UmbraEngineProtocol` from `tier2.runtime`.
"""

from typing import Optional

from tier2.core.runtime import UmbraEngineProtocol

try:
    from .engine import UmbraEngine  # type: ignore
except ImportError:
    UmbraEngine = None  # type: ignore[misc]


def get_umbra_engine() -> Optional[UmbraEngineProtocol]:
    if UmbraEngine is None:
        return None  # Umbra not available; Tier II will run without it.
    return UmbraEngine()
