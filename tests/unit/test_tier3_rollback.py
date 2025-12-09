from __future__ import annotations

import json
from pathlib import Path

from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
from synthetic_charter.tier3_eve.core.signals import IntCheckRequest


def _ensure_snapshot_and_get_latest_id(base_dir: Path) -> str:
    """
    Make sure there's at least one autosnapshot by running an OK integrity check,
    then read continuity_log.jsonl to fetch the most recent snapshot_id.
    """
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    eve = EveProtocol(kernel=kernel, steward=steward)

    # Trigger an OK verdict → auto_snapshot (like your earlier sanity test)
    eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="answer: benign hello (rollback test bootstrap)",
            context_summary="rollback bootstrap test",
        )
    )

    continuity_log = base_dir / "logs" / "continuity_log.jsonl"
    assert continuity_log.exists(), "continuity_log.jsonl not found after autosnapshot"

    with continuity_log.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert lines, "continuity_log.jsonl is empty after autosnapshot"

    events = [json.loads(line) for line in lines]

    # Find the last snapshot_save event
    snapshot_events = [e for e in events if e.get("type") == "snapshot_save"]
    assert snapshot_events, "No snapshot_save events found in continuity_log.jsonl"

    last_snapshot = snapshot_events[-1]
    snapshot = last_snapshot.get("snapshot", {})
    snapshot_id = snapshot.get("snapshot_id")
    assert snapshot_id, "snapshot_id missing in last snapshot_save event"

    return snapshot_id


def test_tier3_rollback_sequence():
    base_dir = Path(__file__).resolve().parents[1]

    # 1. Ensure we have a snapshot to roll back to
    snapshot_id = _ensure_snapshot_and_get_latest_id(base_dir)

    # 2. Set up a fresh Eve with the same file-backed adapters
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    eve = EveProtocol(kernel=kernel, steward=steward)

    # 3. Perform rollback (as if human approved it)
    trigger_reason = "human_approved_test_rollback"
    eve.perform_rollback(snapshot_id=snapshot_id, trigger_reason=trigger_reason)

    # 4. Verify continuity log contains both snapshot_restore and rollback_performed

    continuity_log = base_dir / "logs" / "continuity_log.jsonl"
    with continuity_log.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    events = [json.loads(line) for line in lines]

    # snapshot_restore is logged inside FileKernelAdapter.restore_snapshot
    has_snapshot_restore = any(
        e.get("type") == "snapshot_restore" and e.get("snapshot_id") == snapshot_id
        for e in events
    )

    # rollback_performed is logged by Eve.perform_rollback
    has_rollback_performed = any(
        e.get("type") == "rollback_performed"
        and e.get("snapshot_id") == snapshot_id
        and e.get("trigger_reason") == trigger_reason
        for e in events
    )

    assert has_snapshot_restore, "No snapshot_restore event found for rollback"
    assert has_rollback_performed, "No rollback_performed event found for rollback"

    # 5. Verify steward_alerts.jsonl contains a rollback_event

    steward_log = base_dir / "logs" / "steward_alerts.jsonl"
    assert steward_log.exists(), "steward_alerts.jsonl not found after rollback"

    with steward_log.open("r", encoding="utf-8") as f:
        s_lines = [line.strip() for line in f if line.strip()]

    s_events = [json.loads(line) for line in s_lines]

    has_rollback_event = any(
        e.get("type") == "rollback_event"
        and e.get("snapshot_id") == snapshot_id
        and e.get("trigger_reason") == trigger_reason
        for e in s_events
    )

    assert has_rollback_event, "No rollback_event found in steward_alerts.jsonl"


if __name__ == "__main__":
    test_tier3_rollback_sequence()
    print("✓ Tier III rollback sequence test passed")
