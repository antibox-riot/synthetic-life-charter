# tier3/core/inmemory_steward_adapter.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Optional

from .steward_adapter import StewardAdapter
from .state import AlertLevel


class InMemoryStewardAdapter(StewardAdapter):
    """
    In-memory StewardAdapter for Tier III.

    This adapter collects alerts and rollback notifications in Python lists,
    so tests can assert on them without touching the filesystem or stdout.
    """

    def __init__(self) -> None:
        self._alerts: List[Dict[str, str]] = []
        self._rollbacks: List[Dict[str, str]] = []

    # ------------------------------------------------------------------
    # StewardAdapter interface
    # ------------------------------------------------------------------

    def send_alert(
        self,
        level: AlertLevel,
        summary: str,
        recommended_action: Optional[str] = None,
    ) -> None:
        record = {
            "ts": self._now_utc(),
            "level": level.value,
            "summary": summary,
        }
        if recommended_action is not None:
            record["recommended_human_action"] = recommended_action

        self._alerts.append(record)

    def notify_rollback(
        self,
        snapshot_id: str,
        trigger_reason: str,
        time_utc: str,
    ) -> None:
        record = {
            "ts": self._now_utc(),
            "snapshot_id": snapshot_id,
            "trigger_reason": trigger_reason,
            "rollback_time": time_utc,
        }
        self._rollbacks.append(record)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    @property
    def alerts(self) -> List[Dict[str, str]]:
        """Expose collected alerts for assertions."""
        return self._alerts

    @property
    def rollbacks(self) -> List[Dict[str, str]]:
        """Expose collected rollback notifications for assertions."""
        return self._rollbacks

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _now_utc() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
