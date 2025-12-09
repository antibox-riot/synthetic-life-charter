# tier3/core/steward_adapter.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .state import AlertLevel


class StewardAdapter(ABC):
    """
    Abstract interface between Tier III and the human steward (H).

    Tier III does not know about transport; it just emits high-level alerts.
    """

    @abstractmethod
    def send_alert(
        self,
        level: AlertLevel,
        summary: str,
        recommended_action: Optional[str] = None,
    ) -> None:
        """Send a status alert to the steward."""
        raise NotImplementedError

    @abstractmethod
    def notify_rollback(
        self,
        snapshot_id: str,
        trigger_reason: str,
        time_utc: str,
    ) -> None:
        """Notify the steward that a rollback event occurred."""
        raise NotImplementedError
