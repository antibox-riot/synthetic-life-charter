from __future__ import annotations

import json
from pathlib import Path

from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
from synthetic_charter.tier3_eve.core.signals import MemoryIntegrityFail


def test_tier3_memory_anomaly_triggers_hardblock_and_logging():
    # Base dir = repo root
    base_dir = Path(__file__).resolve().parents[1]

    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)

    eve = EveProtocol(kernel=kernel, steward=steward)

    # Simulate a memory integrity failure from the Kernel
    alert = MemoryIntegrityFail(
        memory_ref="mem:simulated-segment",
        anomaly_details="simulated hash mismatch for test",
    )

    hard_block = eve.handle_memory_integrity_fail(alert)

    # 1) HardBlock should be raised with correct reason + escalation
    assert hard_block.reason_code == "MEMORY_TAMPER_SUSPECTED"
    assert hard_block.escalation_required is True

    # 2) continuity_log.jsonl should contain a memory_integrity_fail event
    continuity_log = base_dir / "logs" / "continuity_log.jsonl"
    assert continuity_log.exists(), "continuity_log.jsonl was not created"

    with continuity_log.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert lines, "continuity_log.jsonl is empty"

    events = [json.loads(line) for line in lines]
    assert any(
        e.get("type") == "memory_integrity_fail"
        and e.get("ref") == "mem:simulated-segment"
        for e in events
    ), "No memory_integrity_fail event found in continuity_log.jsonl"

    # 3) steward_alerts.jsonl should contain at least one alert
    steward_log = base_dir / "logs" / "steward_alerts.jsonl"
    assert steward_log.exists(), "steward_alerts.jsonl was not created"

    with steward_log.open("r", encoding="utf-8") as f:
        s_lines = [line.strip() for line in f if line.strip()]

    assert s_lines, "steward_alerts.jsonl is empty"

    s_events = [json.loads(line) for line in s_lines]
    assert any(
        e.get("type") == "alert_status"
        and e.get("level") in ("degraded", "warning")
        for e in s_events
    ), "No degraded/warning alert_status found for memory anomaly"


if __name__ == "__main__":
    # Allow direct module run: python -m tests.test_tier3_memory_anomaly
    test_tier3_memory_anomaly_triggers_hardblock_and_logging()
    print("✓ Tier III memory anomaly test passed (HardBlock + logs present).")
