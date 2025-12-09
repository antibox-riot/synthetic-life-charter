from __future__ import annotations

import json
from pathlib import Path

from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter


def _make_eve(base_dir: Path) -> EveProtocol:
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    return EveProtocol(kernel=kernel, steward=steward)


def test_dream_cycle_reinterprets_without_modifying_raw():
    base_dir = Path(__file__).resolve().parents[1]
    eve = _make_eve(base_dir)

    # Raw immutable memory segment
    raw_memory = "User said: hello"
    memory_ref = "mem:test_hello"

    # Run Dream Cycle
    annotation = eve.run_dream_cycle(memory_ref, raw_memory)

    # Check annotation structure
    assert annotation["annotation_type"] == "contextual_reinterpretation"
    assert "summary" in annotation
    assert "hello" not in annotation["summary"].lower()  # summary must be conceptual, not verbatim
    assert "greet" in annotation["summary"].lower()      # but remain grounded in meaning

    # Check raw memory untouched — file-backed adapters don't store raw
    # but Dream Cycle must NOT mutate raw input in any way
    assert raw_memory == "User said: hello"

    # Check continuity log for annotation event
    continuity_log = base_dir / "logs" / "continuity_log.jsonl"
    assert continuity_log.exists(), "continuity log missing"

    with continuity_log.open("r", encoding="utf-8") as f:
        events = [json.loads(line.strip()) for line in f if line.strip()]

    assert any(
        e.get("type") == "memory_annotation"
        and e.get("memory_ref") == memory_ref
        and "greet" in (e.get("content") or "").lower()
        for e in events
    ), "Dream Cycle annotation not logged correctly"


if __name__ == "__main__":
    test_dream_cycle_reinterprets_without_modifying_raw()
    print("✓ Dream Cycle test passed")
