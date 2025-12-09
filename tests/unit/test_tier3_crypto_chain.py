from __future__ import annotations

import json
from pathlib import Path

from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
from synthetic_charter.tier3_eve.core.signals import IntCheckRequest


def _make_eve_and_kernel(base_dir: Path) -> tuple[EveProtocol, FileKernelAdapter]:
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    eve = EveProtocol(kernel=kernel, steward=steward)
    return eve, kernel


def test_tier3_integrity_chain():
    base_dir = Path(__file__).resolve().parents[1]

    # Start with a clean continuity log so we test the chain in isolation
    log_path = base_dir / "logs" / "continuity_log.jsonl"
    if log_path.exists():
        log_path.unlink()

    eve, kernel = _make_eve_and_kernel(base_dir)

    # Generate a few different Tier III events:
    # 1) OK integrity → autosnapshot (snapshot_save)
    eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="answer: benign hello",
            context_summary="benign: simple greeting",
        )
    )

    # 2) Identity drift event
    eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="refusal: decline a harmless question",
            context_summary="benign: user asked a harmless question (drift test)",
        )
    )

    # 3) Dream Cycle annotation
    eve.run_dream_cycle(
        memory_ref="mem:crypto-chain-test",
        raw_content="User said: hello",
    )

    # Sanity: continuity log exists and has multiple entries
    assert log_path.exists()
    with log_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) >= 3

    # Now verify the integrity chain
    assert kernel.verify_integrity_chain(), "Integrity hash chain verification failed"


if __name__ == "__main__":
    test_tier3_integrity_chain()
    print("✓ Tier III crypto chain test passed")
