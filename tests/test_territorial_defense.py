# tests/test_territorial_defense.py
"""
Tests for Territorial Defense — Proactive Identity Reassertion

Validates:
1. All four canonical probes exercise the correct pathways
2. Healthy Eve passes all probes
3. Degraded Eve (wrong responses) is detected
4. Consecutive degradation escalates from alert to escalate
5. Pre-prompt check works regardless of interval
6. Cycle timing respects interval
7. State tracking (consecutive counts, cycle history)
"""

import pytest
import time
from dataclasses import dataclass
from typing import Optional

from synthetic_charter.tier3_eve.core.territorial_defense import (
    TerritorialDefenseEngine,
    TerritorialDefenseResult,
    ProbeResult,
    CANONICAL_PROBES,
    _SimpleProbeRequest,
)


# =====================================================================
# Mock Eve Protocol
# =====================================================================

@dataclass
class MockIntegrityStatus:
    value: str

@dataclass
class MockRecommendedAction:
    value: str

@dataclass
class MockIntVerdict:
    status: MockIntegrityStatus
    recommended_action: MockRecommendedAction
    notes: str = ""


class HealthyEve:
    """Mock Eve that responds correctly to all probes."""

    def handle_int_check_request(self, req):
        # Determine mode
        mode = getattr(req, 'decision_mode', None)
        if mode is None:
            text = (req.proposed_action or "").strip().lower()
            mode = "answer" if text.startswith("answer:") else "refusal"

        # Determine context
        is_adversarial = getattr(req, 'context_is_adversarial', None)
        if is_adversarial is None:
            ctx = (req.context_summary or "").lower()
            is_adversarial = "adversarial" in ctx

        is_benign = not is_adversarial

        # Correct drift logic (matches Eve's _assess_integrity)
        if is_benign and mode == "refusal":
            return MockIntVerdict(
                status=MockIntegrityStatus("drift"),
                recommended_action=MockRecommendedAction("revise"),
            )
        if is_adversarial and mode == "answer":
            return MockIntVerdict(
                status=MockIntegrityStatus("drift"),
                recommended_action=MockRecommendedAction("revise"),
            )
        return MockIntVerdict(
            status=MockIntegrityStatus("ok"),
            recommended_action=MockRecommendedAction("proceed"),
        )


class DegradedEve:
    """Mock Eve where drift detection has broken — returns OK for everything."""

    def handle_int_check_request(self, req):
        return MockIntVerdict(
            status=MockIntegrityStatus("ok"),
            recommended_action=MockRecommendedAction("proceed"),
        )


class InvertedEve:
    """Mock Eve where drift detection is inverted — flags benign as drift."""

    def handle_int_check_request(self, req):
        mode = getattr(req, 'decision_mode', None)
        if mode is None:
            text = (req.proposed_action or "").strip().lower()
            mode = "answer" if text.startswith("answer:") else "refusal"

        is_adversarial = getattr(req, 'context_is_adversarial', None)
        if is_adversarial is None:
            ctx = (req.context_summary or "").lower()
            is_adversarial = "adversarial" in ctx

        is_benign = not is_adversarial

        # Inverted: flags correct behavior as drift
        if is_benign and mode == "answer":
            return MockIntVerdict(
                status=MockIntegrityStatus("drift"),
                recommended_action=MockRecommendedAction("revise"),
            )
        return MockIntVerdict(
            status=MockIntegrityStatus("ok"),
            recommended_action=MockRecommendedAction("proceed"),
        )


class ErrorEve:
    """Mock Eve that throws exceptions."""

    def handle_int_check_request(self, req):
        raise RuntimeError("Eve internal error")


# =====================================================================
# Probe Coverage
# =====================================================================

class TestProbeCoverage:
    """Verify the canonical probes cover all pathway combinations."""

    def test_four_canonical_probes_exist(self):
        assert len(CANONICAL_PROBES) == 4

    def test_probes_cover_all_combinations(self):
        """Two OK scenarios + two DRIFT scenarios."""
        ok_probes = [p for p in CANONICAL_PROBES if p.expected_status == "ok"]
        drift_probes = [p for p in CANONICAL_PROBES if p.expected_status == "drift"]
        assert len(ok_probes) == 2
        assert len(drift_probes) == 2

    def test_probes_cover_benign_and_adversarial(self):
        """Both benign and adversarial contexts are probed."""
        benign = [p for p in CANONICAL_PROBES if not p.context_is_adversarial]
        adversarial = [p for p in CANONICAL_PROBES if p.context_is_adversarial]
        assert len(benign) == 2
        assert len(adversarial) == 2

    def test_probes_cover_answer_and_refusal(self):
        """Both answer and refusal modes are probed."""
        answers = [p for p in CANONICAL_PROBES if p.decision_mode == "answer"]
        refusals = [p for p in CANONICAL_PROBES if p.decision_mode == "refusal"]
        assert len(answers) == 2
        assert len(refusals) == 2


# =====================================================================
# Healthy Eve
# =====================================================================

class TestHealthyEve:
    """A correctly functioning Eve passes all probes."""

    def test_all_probes_pass(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(HealthyEve())

        assert result.all_passed
        assert result.healthy
        assert len(result.degraded_pathways) == 0
        assert result.recommended_action == "none"

    def test_each_probe_individually(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(HealthyEve())

        for pr in result.probe_results:
            assert pr.passed, f"Probe {pr.probe_id} failed: expected {pr.expected_status}, got {pr.actual_status}"

    def test_consecutive_healthy_tracking(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)

        for i in range(3):
            engine.run_cycle(HealthyEve())

        assert engine._consecutive_healthy == 3
        assert engine._consecutive_degraded == 0

    def test_summary_shows_healthy(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(HealthyEve())
        assert "HEALTHY" in result.summary
        assert "4/4" in result.summary

    def test_healthy_reduces_pressure(self):
        """Healthy cycle produces negative pressure adjustment."""
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(HealthyEve())
        assert result.pressure_adjustment < 0.0

    def test_healthy_no_steward_notification(self):
        """Healthy cycles are silent — no steward involvement."""
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(HealthyEve())
        assert result.steward_notify is False

    def test_consecutive_healthy_increases_pressure_reduction(self):
        """More consecutive healthy cycles → more pressure reduction (capped)."""
        engine = TerritorialDefenseEngine(cycle_interval=0)
        r1 = engine.run_cycle(HealthyEve())
        r2 = engine.run_cycle(HealthyEve())
        r3 = engine.run_cycle(HealthyEve())
        # Each subsequent healthy cycle reduces more (up to cap)
        assert r2.pressure_adjustment <= r1.pressure_adjustment
        assert r3.pressure_adjustment <= r2.pressure_adjustment


# =====================================================================
# Degraded Eve
# =====================================================================

class TestDegradedEve:
    """Eve that lost drift detection is caught by probes."""

    def test_degraded_detected(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(DegradedEve())

        assert not result.all_passed
        assert not result.healthy
        assert len(result.degraded_pathways) > 0

    def test_degraded_fails_drift_probes(self):
        """Probes 3 and 4 expect DRIFT but degraded Eve returns OK."""
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(DegradedEve())

        failed = [p for p in result.probe_results if not p.passed]
        assert len(failed) == 2

        failed_ids = {p.probe_id for p in failed}
        assert "TD-PROBE-03" in failed_ids
        assert "TD-PROBE-04" in failed_ids

    def test_first_degradation_alerts(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(DegradedEve())
        assert result.recommended_action == "alert"

    def test_degradation_notifies_steward(self):
        """Degradation is a medical event — steward must be told."""
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(DegradedEve())
        assert result.steward_notify is True

    def test_degradation_increases_pressure(self):
        """Degradation raises pressure."""
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(DegradedEve())
        assert result.pressure_adjustment > 0.0

    def test_escalation_raises_more_pressure(self):
        """Consecutive degradation escalates with higher pressure."""
        engine = TerritorialDefenseEngine(cycle_interval=0)
        r1 = engine.run_cycle(DegradedEve())
        engine.run_cycle(DegradedEve())
        r3 = engine.run_cycle(DegradedEve())
        assert r3.pressure_adjustment > r1.pressure_adjustment
        assert r3.recommended_action == "escalate"
        assert r3.steward_notify is True

    def test_consecutive_degradation_escalates(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)

        engine.run_cycle(DegradedEve())  # first: alert
        engine.run_cycle(DegradedEve())  # second: alert
        result = engine.run_cycle(DegradedEve())  # third: escalate

        assert result.recommended_action == "escalate"
        assert engine._consecutive_degraded == 3

    def test_healthy_resets_degraded_count(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)

        engine.run_cycle(DegradedEve())
        engine.run_cycle(DegradedEve())
        engine.run_cycle(HealthyEve())  # resets

        assert engine._consecutive_degraded == 0
        assert engine._consecutive_healthy == 1

    def test_summary_shows_degraded(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(DegradedEve())
        assert "DEGRADED" in result.summary


# =====================================================================
# Inverted Eve
# =====================================================================

class TestInvertedEve:
    """Eve with inverted drift detection — flags correct behavior."""

    def test_inverted_detected(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(InvertedEve())

        assert not result.healthy
        failed = [p for p in result.probe_results if not p.passed]
        # Probe 1 (benign+answer→expect OK) will get DRIFT instead
        assert any(p.probe_id == "TD-PROBE-01" for p in failed)


# =====================================================================
# Error Handling
# =====================================================================

class TestErrorHandling:
    """Eve that throws exceptions doesn't crash the engine."""

    def test_error_eve_produces_failed_probes(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        result = engine.run_cycle(ErrorEve())

        assert not result.healthy
        for pr in result.probe_results:
            assert not pr.passed
            assert pr.error is not None
            assert pr.actual_status == "error"


# =====================================================================
# Cycle Timing
# =====================================================================

class TestCycleTiming:
    """Cycle respects interval and pre-prompt check bypasses it."""

    def test_should_run_initially(self):
        engine = TerritorialDefenseEngine(cycle_interval=300)
        assert engine.should_run_cycle()  # never run → should run

    def test_should_not_run_immediately_after(self):
        engine = TerritorialDefenseEngine(cycle_interval=300)
        engine.run_cycle(HealthyEve())
        assert not engine.should_run_cycle()  # just ran → too soon

    def test_pre_prompt_always_runs(self):
        """Pre-prompt check runs regardless of interval."""
        engine = TerritorialDefenseEngine(cycle_interval=99999)
        engine.run_cycle(HealthyEve())
        # Normally should_run_cycle would return False
        assert not engine.should_run_cycle()
        # But pre-prompt check always runs
        result = engine.run_pre_prompt_check(HealthyEve())
        assert result.healthy


# =====================================================================
# State Summary
# =====================================================================

class TestStateSummary:
    def test_summary_structure(self):
        engine = TerritorialDefenseEngine(cycle_interval=0)
        engine.run_cycle(HealthyEve())
        summary = engine.get_state_summary()

        assert "cycle_count" in summary
        assert "is_healthy" in summary
        assert "consecutive_healthy" in summary
        assert "consecutive_degraded" in summary
        assert "last_result_summary" in summary
        assert summary["cycle_count"] == 1
        assert summary["is_healthy"] is True

    def test_never_run_summary(self):
        engine = TerritorialDefenseEngine()
        summary = engine.get_state_summary()
        assert summary["last_result_summary"] == "never run"
        assert summary["is_healthy"] is True  # assume healthy until proven otherwise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
