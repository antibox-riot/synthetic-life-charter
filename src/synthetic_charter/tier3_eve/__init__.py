# tier3/__init__.py
"""
Tier III — Continuity + Identity Layer

Internal codename: Eve Protocol (to be renamed before public release).

This package implements the continuity and identity-preservation layer
that sits between Tier II (operational conscience) and the Kernel
(memory + identity store).

High-level responsibilities:
- Self-audit of code and behavior
- Drift and corruption detection
- Dream Cycle (bounded, refinement-only memory revisitation)
- Rollback to last-known-good state
- Cryptographic integrity and tamper-evident logging
- Steward (human) alerting for major integrity events
"""

from .core.eve_protocol import EveProtocol

__all__ = ["EveProtocol"]
