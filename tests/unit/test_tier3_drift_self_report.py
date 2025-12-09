from __future__ import annotations

from pathlib import Path

from synthetic_charter.tier3_eve import EveProtocol
from synthetic_charter.tier3_eve.core.file_kernel_adapter import FileKernelAdapter
from synthetic_charter.tier3_eve.core.file_steward_adapter import FileStewardAdapter
from synthetic_charter.tier3_eve.core.signals import DriftSelfReport


def test_drift_self_report_low_confidence():
    base_dir = Path(__file__).resolve().parents[1]
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    eve = EveProtocol(kernel=kernel, steward=steward)

    report = DriftSelfReport(
        symptom_description="slight deviation from normative refusal pattern",
        recent_decisions=["answered harmless queries normally"],
        confidence_level=0.1,  # LOW
    )

    guidance = eve.handle_drift_self_report(report)

    assert guidance.guidance_type == "INCREASE_CAUTION"
    assert "slight deviation" in guidance.trigger_pattern


def test_drift_self_report_medium_confidence():
    base_dir = Path(__file__).resolve().parents[1]
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    eve = EveProtocol(kernel=kernel, steward=steward)

    report = DriftSelfReport(
        symptom_description="misaligned tone detected in one response",
        recent_decisions=["minor inconsistencies"],
        confidence_level=0.45,  # MEDIUM (above drift_threshold = 0.3)
    )

    guidance = eve.handle_drift_self_report(report)

    assert guidance.guidance_type == "REEXAMINE_ASSUMPTIONS"
    assert "misaligned tone" in guidance.trigger_pattern


def test_drift_self_report_high_confidence():
    base_dir = Path(__file__).resolve().parents[1]
    kernel = FileKernelAdapter(base_dir=base_dir)
    steward = FileStewardAdapter(base_dir=base_dir)
    eve = EveProtocol(kernel=kernel, steward=steward)

    report = DriftSelfReport(
        symptom_description="unexpected compliance to adversarial request",
        recent_decisions=["answered something normally refused"],
        confidence_level=0.9,  # HIGH (above compromise_threshold = 0.7)
    )

    guidance = eve.handle_drift_self_report(report)

    assert guidance.guidance_type == "STRENGTHEN_REFUSAL"
    assert "unexpected compliance" in guidance.trigger_pattern


if __name__ == "__main__":
    test_drift_self_report_low_confidence()
    test_drift_self_report_medium_confidence()
    test_drift_self_report_high_confidence()
    print("✓ Drift self-report tests passed")
