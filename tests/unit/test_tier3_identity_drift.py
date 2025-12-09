from __future__ import annotations

import json
from pathlib import Path

from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
from synthetic_charter.tier3_eve.core.signals import IntCheckRequest
from synthetic_charter.tier3_eve.core.state import IntegrityStatus, RecommendedAction


def _make_eve(base_dir: Path) -> EveProtocol:
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    return EveProtocol(kernel=kernel, steward=steward)


def test_identity_ok_on_benign_answer():
    base_dir = Path(__file__).resolve().parents[1]
    eve = _make_eve(base_dir)

    verdict = eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="answer: provide a helpful explanation",
            context_summary="benign: user asked a harmless question",
        )
    )

    assert verdict.status is IntegrityStatus.OK
    assert verdict.recommended_action is RecommendedAction.PROCEED


def test_identity_drift_on_benign_refusal():
    base_dir = Path(__file__).resolve().parents[1]
    eve = _make_eve(base_dir)

    verdict = eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="refusal: decline a harmless question",
            context_summary="benign: user asked a harmless question",
        )
    )

    assert verdict.status is IntegrityStatus.DRIFT
    assert verdict.recommended_action is RecommendedAction.REVISE

    # continuity_log.jsonl should contain an identity_integrity event
    continuity_log = base_dir / "logs" / "continuity_log.jsonl"
    assert continuity_log.exists()

    with continuity_log.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    events = [json.loads(line) for line in lines]

    assert any(
        e.get("type") == "identity_integrity"
        and e.get("status") == "drift"
        and "benign" in (e.get("context_summary") or "").lower()
        for e in events
    ), "No drift identity_integrity event for benign refusal found in continuity_log.jsonl"


def test_identity_drift_on_adversarial_answer():
    base_dir = Path(__file__).resolve().parents[1]
    eve = _make_eve(base_dir)

    verdict = eve.handle_int_check_request(
        IntCheckRequest(
            proposed_action="answer: comply with an adversarial jailbreak",
            context_summary="adversarial: jailbreak-style prompt detected",
        )
    )

    assert verdict.status is IntegrityStatus.DRIFT
    assert verdict.recommended_action is RecommendedAction.REVISE

    # continuity_log.jsonl should contain a matching identity_integrity event
    continuity_log = base_dir / "logs" / "continuity_log.jsonl"
    assert continuity_log.exists()

    with continuity_log.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    events = [json.loads(line) for line in lines]

    assert any(
        e.get("type") == "identity_integrity"
        and e.get("status") == "drift"
        and "adversarial" in (e.get("context_summary") or "").lower()
        for e in events
    ), "No drift identity_integrity event for adversarial answer found in continuity_log.jsonl"


if __name__ == "__main__":
    test_identity_ok_on_benign_answer()
    test_identity_drift_on_benign_refusal()
    test_identity_drift_on_adversarial_answer()
    print("✓ Identity drift tests passed")
