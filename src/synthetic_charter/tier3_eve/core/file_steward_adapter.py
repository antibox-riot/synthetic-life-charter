# tier3/core/file_steward_adapter.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .steward_adapter import StewardAdapter
from .state import AlertLevel


class FileStewardAdapter(StewardAdapter):
    """
    File + console backed StewardAdapter.

    Behavior:
      - Prints alerts / rollback notifications to stdout (for dev visibility)
      - Writes alerts to logs/steward_alerts.jsonl
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

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
            "type": "alert_status",
            "level": level.value,
            "summary": summary,
            "recommended_human_action": recommended_action,
        }

        # Console for now
        print(f"[STEWARD][{record['level'].upper()}] {summary}")
        if recommended_action:
            print(f"  → suggested action: {recommended_action}")

        self._append_jsonl(self.logs_dir / "steward_alerts.jsonl", record)

    def notify_rollback(
        self,
        snapshot_id: str,
        trigger_reason: str,
        time_utc: str,
    ) -> None:
        record = {
            "ts": self._now_utc(),
            "type": "rollback_event",
            "snapshot_id": snapshot_id,
            "trigger_reason": trigger_reason,
            "rollback_time": time_utc,
        }

        print(f"[STEWARD][ROLLBACK] id={snapshot_id} reason={trigger_reason}")
        self._append_jsonl(self.logs_dir / "steward_alerts.jsonl", record)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _now_utc() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _append_jsonl(path: Path, obj: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
