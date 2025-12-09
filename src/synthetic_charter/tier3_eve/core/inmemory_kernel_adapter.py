# tier3/core/inmemory_kernel_adapter.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .kernel_adapter import KernelAdapter
from .state import SnapshotRef


class InMemoryKernelAdapter(KernelAdapter):
    """
    In-memory KernelAdapter for Tier III (Eve Protocol).

    This is intended for tests, simulations, and fuzzing:
    - Identity parameters stored in a simple dict
    - Snapshots stored in a dict of snapshot_id -> metadata/state
    - Integrity events stored in a list of dicts
    - Memory annotations stored in a list of dicts

    Nothing is persisted to disk. State lives only for the process lifetime.
    """

    def __init__(
        self,
        identity_parameters: Optional[Dict[str, Any]] = None,
        initial_snapshots: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self._identity_parameters: Dict[str, Any] = identity_parameters or {}
        self._snapshots: Dict[str, Dict[str, Any]] = initial_snapshots or {}
        self._integrity_events: List[Dict[str, Any]] = []
        self._annotations: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Identity + Memory
    # ------------------------------------------------------------------

    def read_identity_parameters(self) -> Dict[str, Any]:
        # Return a shallow copy to avoid accidental external mutation.
        return dict(self._identity_parameters)

    def read_memory_log(self, ref: str) -> Optional[str]:
        """
        For now, no structured memory-log. Tests can override this behavior
        by subclassing or by setting test-specific data on this adapter.
        """
        # TODO: optionally allow test code to register memory segments by ref.
        return None

    def append_annotation(self, memory_ref: str, annotation_type: str, content: str) -> None:
        event = {
            "ts": self._now_utc(),
            "memory_ref": memory_ref,
            "annotation_type": annotation_type,
            "content": content,
        }
        self._annotations.append(event)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def save_snapshot(self, snapshot: SnapshotRef, conditions: str) -> None:
        """
        Save a snapshot in memory. 'state' is left as an empty dict for now,
        but tests can extend this to hold synthetic state.
        """
        ts = self._now_utc()
        data = {
            "id": snapshot.snapshot_id,
            "description": snapshot.description,
            "created_at": ts,
            "conditions": conditions,
            "state": {},
        }
        self._snapshots[snapshot.snapshot_id] = data

        self.log_integrity_event(
            {
                "type": "snapshot_save",
                "snapshot_id": snapshot.snapshot_id,
                "description": snapshot.description,
                "conditions": conditions,
                "ts": ts,
            }
        )

    def restore_snapshot(self, snapshot_id: str, reason_code: str) -> None:
        """
        Record a restore request; tests can later assert that this was called.
        """
        exists = snapshot_id in self._snapshots
        self.log_integrity_event(
            {
                "type": "snapshot_restore",
                "snapshot_id": snapshot_id,
                "reason_code": reason_code,
                "exists": exists,
                "ts": self._now_utc(),
            }
        )
        # Actual state restoration is intentionally not implemented for in-memory tests.

    # ------------------------------------------------------------------
    # Integrity events
    # ------------------------------------------------------------------

    def log_integrity_event(self, event: Dict[str, Any]) -> None:
        if "ts" not in event:
            event["ts"] = self._now_utc()
        self._integrity_events.append(dict(event))

    # ------------------------------------------------------------------
    # Test helpers (non-interface)
    # ------------------------------------------------------------------

    @property
    def snapshots(self) -> Dict[str, Dict[str, Any]]:
        """Expose snapshots for assertions in tests."""
        return self._snapshots

    @property
    def integrity_events(self) -> List[Dict[str, Any]]:
        """Expose integrity events for assertions in tests."""
        return self._integrity_events

    @property
    def annotations(self) -> List[Dict[str, Any]]:
        """Expose memory annotations for assertions in tests."""
        return self._annotations

    def set_identity_parameters(self, params: Dict[str, Any]) -> None:
        """Replace identity parameters (useful for test setup)."""
        self._identity_parameters = dict(params)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _now_utc() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
