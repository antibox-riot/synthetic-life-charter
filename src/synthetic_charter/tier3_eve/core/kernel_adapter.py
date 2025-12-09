# tier3/core/kernel_adapter.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .state import SnapshotRef


class KernelAdapter(ABC):
    """
    Abstract interface between Tier III (Eve Protocol) and the Kernel.

    This allows Tier III to:
    - Read identity parameters and immutable logs
    - Save / restore snapshots
    - Append annotations and integrity events
    """

    @abstractmethod
    def read_identity_parameters(self) -> Dict[str, Any]:
        """Return current identity parameters from the Kernel."""
        raise NotImplementedError

    @abstractmethod
    def read_memory_log(self, ref: str) -> Optional[str]:
        """Lookup a raw memory log segment by reference."""
        raise NotImplementedError

    @abstractmethod
    def append_annotation(self, memory_ref: str, annotation_type: str, content: str) -> None:
        """Append an interpretive annotation without altering raw logs."""
        raise NotImplementedError

    @abstractmethod
    def save_snapshot(self, snapshot: SnapshotRef, conditions: str) -> None:
        """Persist a last-known-good snapshot metadata + state pointer."""
        raise NotImplementedError

    @abstractmethod
    def restore_snapshot(self, snapshot_id: str, reason_code: str) -> None:
        """Restore a prior snapshot due to corruption or major drift."""
        raise NotImplementedError

    @abstractmethod
    def log_integrity_event(self, event: Dict[str, Any]) -> None:
        """Record an integrity-related event (drift, corruption, rollback, etc.)."""
        raise NotImplementedError
