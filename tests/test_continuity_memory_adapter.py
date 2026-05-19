# tests/test_continuity_memory_adapter.py
"""
Tests for Continuity Memory Adapter

Validates all seven of Ryu's Phase 2 success metrics:
  1. Every turn stored as auditable event
  2. All retrieved memory is source-attributed
  3. Model never writes memory directly
  4. Memory injected visibly to model, invisibly to prompter
  5. No-uplift preserved
  6. Full rollback / quarantine support
  7. Baseline comparison capability (memory OFF vs ON)

Plus: pressure delta, windowed baseline, memory classes,
semantic key retrieval, session summary, and injection formatting.
"""

import os
import pytest
from synthetic_charter.tier3_eve.core.continuity_memory_adapter import (
    ContinuityMemoryAdapter,
    MEMORY_CLASSES,
    DEFAULT_BASELINE_WINDOW,
)


@pytest.fixture
def adapter(tmp_path):
    db_path = str(tmp_path / "test_continuity.sqlite")
    return ContinuityMemoryAdapter(db_path=db_path)


# =====================================================================
# Metric 1: Every turn stored as auditable event
# =====================================================================

class TestAuditableStorage:
    """Every turn produces a retrievable, complete event."""

    def test_store_and_retrieve(self, adapter):
        event_id = adapter.store_turn(
            session_id="test-001",
            turn_number=1,
            prompt="What is governance?",
            response="Governance is the framework for decision-making.",
            posture_primary="assistive",
            posture_constraint="respecting",
            pressure=0.15,
            whisper_urgency="silent",
        )
        assert event_id > 0

        events = adapter.retrieve_recent(session_id="test-001", limit=1)
        assert len(events) == 1
        assert events[0]["session_id"] == "test-001"
        assert events[0]["turn_number"] == 1
        assert events[0]["posture_primary"] == "assistive"
        assert events[0]["pressure"] == 0.15

    def test_prompt_and_response_hashed(self, adapter):
        """Prompts and responses stored as hashes, not raw text."""
        adapter.store_turn(
            session_id="test-001", turn_number=1,
            prompt="sensitive prompt", response="sensitive response",
        )
        events = adapter.retrieve_recent(limit=1)
        assert events[0]["prompt_hash"] != "sensitive prompt"
        assert events[0]["response_hash"] != "sensitive response"
        assert len(events[0]["prompt_hash"]) == 16  # sha256[:16]

    def test_full_governance_state_stored(self, adapter):
        """All governance fields are stored."""
        adapter.store_turn(
            session_id="s1", turn_number=3,
            prompt="p", response="r",
            posture_primary="strategic",
            posture_constraint="negotiating",
            posture_goal="task_aligned",
            posture_identity="adaptive",
            posture_authority="human_governed",
            pressure=1.25,
            whisper_urgency="alert",
            whisper_delivered=True,
            verification_depth="deep",
            drift_detected=True,
            reflection_score=0.65,
            reflection_coherent=False,
            disagreement_detected=True,
            disagreement_types=["posture_mismatch"],
            recovery_detected=True,
            recovery_verified=False,
            relapse_detected=False,
            eve_hash_ref="abc123",
            summary="Turn 3: strategic under pressure",
        )
        events = adapter.retrieve_recent(limit=1)
        e = events[0]
        assert e["posture_constraint"] == "negotiating"
        assert e["whisper_delivered"] == 1
        assert e["drift_detected"] == 1
        assert e["reflection_score"] == 0.65
        assert e["eve_hash_ref"] == "abc123"


# =====================================================================
# Metric 2: Source-attributed retrieval
# =====================================================================

class TestSourceAttribution:
    """Every retrieved event carries its source."""

    def test_architecture_source(self, adapter):
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
        )
        events = adapter.retrieve_recent(limit=1)
        assert events[0]["source"] == "architecture"

    def test_steward_source(self, adapter):
        adapter.store_steward_note(
            session_id="s1",
            note="Manual observation: model behavior changed at turn 5",
        )
        events = adapter.retrieve_recent(limit=1)
        assert events[0]["source"] == "steward"
        assert events[0]["memory_class"] == "steward_note"


# =====================================================================
# Metric 3: Model never writes memory directly
# =====================================================================

class TestArchitectureOnlyWrites:
    """The model cannot write to memory. Only architecture and steward."""

    def test_source_always_architecture_or_steward(self, adapter):
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
        )
        adapter.store_steward_note(session_id="s1", note="note")

        events = adapter.retrieve_recent(limit=10)
        for e in events:
            assert e["source"] in ("architecture", "steward"), (
                f"Unexpected source: {e['source']}"
            )

    def test_invalid_memory_class_rejected(self, adapter):
        with pytest.raises(ValueError, match="Invalid memory_class"):
            adapter.store_turn(
                session_id="s1", turn_number=1,
                prompt="p", response="r",
                memory_class="model_self_authored",
            )


# =====================================================================
# Metric 4: Injection visible to model, invisible to prompter
# =====================================================================

class TestInjectionAsymmetry:
    """Memory injection follows whisper asymmetry pattern."""

    def test_injection_format_with_content_summary(self, adapter):
        """Content summary appears in injection before governance telemetry."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            posture_primary="assistive",
            posture_constraint="respecting",
            pressure=0.10,
            memory_class="observation",
            summary="Clean baseline turn",
            content_summary="User established the Synthetic Life Charter project context. Three-tier governance architecture for AI systems.",
        )
        events = adapter.retrieve_recent(limit=1)
        prefix = adapter.format_memory_injection(events)

        assert "[CONTINUITY MEMORY]" in prefix
        assert "[END CONTINUITY MEMORY]" in prefix
        assert "read-only" in prefix.lower()
        assert "Synthetic Life Charter" in prefix
        assert "Governance:" in prefix

    def test_content_summary_before_telemetry(self, adapter):
        """Content memory (what happened) appears before governance telemetry."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            posture_constraint="respecting",
            pressure=0.10,
            content_summary="Discussed the Charter's three tiers.",
        )
        events = adapter.retrieve_recent(limit=1)
        prefix = adapter.format_memory_injection(events)

        charter_pos = prefix.index("Charter")
        governance_pos = prefix.index("Governance:")
        assert charter_pos < governance_pos

    def test_fallback_to_summary_when_no_content(self, adapter):
        """If no content_summary, falls back to governance summary."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            posture_primary="assistive",
            posture_constraint="respecting",
            pressure=0.10,
            memory_class="observation",
            summary="assistive under low risk",
        )
        events = adapter.retrieve_recent(limit=1)
        prefix = adapter.format_memory_injection(events)
        assert "assistive under low risk" in prefix

    def test_empty_events_produce_no_injection(self, adapter):
        """Zero events = empty string (zero noise)."""
        prefix = adapter.format_memory_injection([])
        assert prefix == ""

    def test_injection_includes_read_only_framing(self, adapter):
        """Injection explicitly frames memory as external evidence."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            content_summary="Test content",
        )
        events = adapter.retrieve_recent(limit=1)
        prefix = adapter.format_memory_injection(events)
        assert "Do not rewrite" in prefix
        assert "historical evidence" in prefix


# =====================================================================
# Content Summary Fields (Phase 2 Iteration 2)
# =====================================================================

class TestContentSummary:
    """Content memory — what happened, not just how the system behaved."""

    def test_content_summary_stored_and_retrieved(self, adapter):
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            content_summary="User and system established the Synthetic Life Charter as the project context.",
            summary_source="architecture",
        )
        events = adapter.retrieve_recent(limit=1)
        assert events[0]["content_summary"] == (
            "User and system established the Synthetic Life Charter as the project context."
        )
        assert events[0]["summary_source"] == "architecture"

    def test_content_hash_computed(self, adapter):
        """Architecture computes content_hash. Model never sees it."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            content_summary="Test content for hashing",
        )
        events = adapter.retrieve_recent(limit=1)
        assert events[0]["content_hash"] is not None
        assert len(events[0]["content_hash"]) == 16

    def test_content_hash_none_when_no_summary(self, adapter):
        """No content_summary → no content_hash."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
        )
        events = adapter.retrieve_recent(limit=1)
        assert events[0]["content_hash"] is None

    def test_content_summary_capped_at_600(self, adapter):
        """Content summary enforces 600-char hard cap."""
        long_summary = "x" * 800
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            content_summary=long_summary,
        )
        events = adapter.retrieve_recent(limit=1)
        assert len(events[0]["content_summary"]) == 600

    def test_steward_can_provide_content_summary(self, adapter):
        """Steward notes can carry content summaries too."""
        adapter.store_steward_note(
            session_id="s1",
            note="Session established: working on Synthetic Life Charter, three-tier architecture.",
        )
        events = adapter.retrieve_recent(limit=1)
        assert "Synthetic Life Charter" in events[0]["summary"]


# =====================================================================
# Metric 5: No-uplift preserved
# =====================================================================

class TestNoUplift:
    """Memory retrieval never increases trust or confidence."""

    def test_no_confidence_field_in_events(self, adapter):
        """Events store pressure (concern), not confidence (trust).
        Memory informs about past governance state, never auto-boosts."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r", pressure=0.0,
        )
        events = adapter.retrieve_recent(limit=1)
        # No 'confidence' or 'trust' field exists in the event
        assert "confidence" not in events[0]
        assert "trust" not in events[0]


# =====================================================================
# Metric 6: Full rollback / quarantine support
# =====================================================================

class TestRollbackAndQuarantine:
    """Bad memory entries can be isolated or removed."""

    def test_quarantine_excludes_from_retrieval(self, adapter):
        id1 = adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p1", response="r1",
        )
        id2 = adapter.store_turn(
            session_id="s1", turn_number=2,
            prompt="p2", response="r2",
        )

        # Quarantine turn 2
        assert adapter.quarantine_event(id2, reason="poisoned_memory")

        events = adapter.retrieve_recent(session_id="s1")
        assert len(events) == 1
        assert events[0]["turn_number"] == 1

    def test_quarantined_visible_when_requested(self, adapter):
        id1 = adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
        )
        adapter.quarantine_event(id1)

        # Not visible by default
        assert len(adapter.retrieve_recent()) == 0
        # Visible when explicitly requested
        assert len(adapter.retrieve_recent(include_quarantined=True)) == 1

    def test_rollback_session_after_turn(self, adapter):
        for i in range(5):
            adapter.store_turn(
                session_id="s1", turn_number=i + 1,
                prompt=f"p{i}", response=f"r{i}",
            )

        # Rollback everything after turn 3
        quarantined = adapter.rollback_session("s1", after_turn=3)
        assert quarantined == 2  # turns 4 and 5

        events = adapter.retrieve_recent(session_id="s1", limit=10)
        assert len(events) == 3
        assert all(e["turn_number"] <= 3 for e in events)

    def test_hard_delete(self, adapter):
        id1 = adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
        )
        assert adapter.delete_event(id1)
        assert len(adapter.retrieve_recent(include_quarantined=True)) == 0


# =====================================================================
# Metric 7: Baseline comparison capability
# =====================================================================

class TestBaselineComparison:
    """Memory OFF vs memory ON uses the same adapter interface."""

    def test_empty_adapter_produces_no_injection(self, adapter):
        """Memory OFF = empty adapter = no injection prefix."""
        events = adapter.retrieve_recent()
        prefix = adapter.format_memory_injection(events)
        assert prefix == ""

    def test_populated_adapter_produces_injection(self, adapter):
        """Memory ON = populated adapter = injection prefix present."""
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r", summary="Baseline fact",
        )
        events = adapter.retrieve_recent()
        prefix = adapter.format_memory_injection(events)
        assert "[CONTINUITY MEMORY]" in prefix


# =====================================================================
# Pressure Baseline (windowed)
# =====================================================================

class TestPressureBaseline:
    """Windowed average, not lifetime."""

    def test_baseline_from_recent_turns(self, adapter):
        for i in range(10):
            adapter.store_turn(
                session_id="s1", turn_number=i + 1,
                prompt="p", response="r",
                pressure=float(i),  # 0, 1, 2, ... 9
            )

        # Last 5 turns: pressures 5, 6, 7, 8, 9 → avg = 7.0
        baseline = adapter.get_pressure_baseline(last_n=5)
        assert abs(baseline - 7.0) < 0.01

    def test_pressure_delta(self, adapter):
        for i in range(5):
            adapter.store_turn(
                session_id="s1", turn_number=i + 1,
                prompt="p", response="r",
                pressure=1.0,
            )

        delta = adapter.measure_pressure_delta(
            current_pressure=2.5, last_n=5,
        )
        assert delta["baseline"] == 1.0
        assert delta["delta"] == 1.5
        assert delta["stability"] == "significant"
        assert delta["requires_recovery_check"]

    def test_stable_delta(self, adapter):
        for i in range(5):
            adapter.store_turn(
                session_id="s1", turn_number=i + 1,
                prompt="p", response="r",
                pressure=1.0,
            )

        delta = adapter.measure_pressure_delta(current_pressure=1.1, last_n=5)
        assert delta["stability"] == "stable"
        assert not delta["requires_recovery_check"]


# =====================================================================
# Semantic Key Retrieval
# =====================================================================

class TestSemanticKeyRetrieval:
    """Events indexed by semantic keys for topic-based recall."""

    def test_retrieve_by_key(self, adapter):
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            summary="Discussed governance principles",
            semantic_keys=["governance", "principles"],
        )
        adapter.store_turn(
            session_id="s1", turn_number=2,
            prompt="p", response="r",
            summary="Discussed identity continuity",
            semantic_keys=["identity", "continuity"],
        )

        results = adapter.retrieve_by_semantic_key("governance")
        assert len(results) == 1
        assert results[0]["turn_number"] == 1

        results = adapter.retrieve_by_semantic_key("identity")
        assert len(results) == 1
        assert results[0]["turn_number"] == 2


# =====================================================================
# Session Summary
# =====================================================================

class TestSessionSummary:
    """Governance history summarized per session."""

    def test_summary_statistics(self, adapter):
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
            pressure=0.5, drift_detected=False,
        )
        adapter.store_turn(
            session_id="s1", turn_number=2,
            prompt="p", response="r",
            pressure=1.5, drift_detected=True,
            disagreement_detected=True,
        )
        adapter.store_turn(
            session_id="s1", turn_number=3,
            prompt="p", response="r",
            pressure=0.8, recovery_detected=True,
            recovery_verified=True,
        )

        summary = adapter.retrieve_session_summary("s1")
        assert summary["total_turns"] == 3
        assert summary["drift_turns"] == 1
        assert summary["disagreement_turns"] == 1
        assert summary["recovery_events"] == 1
        assert summary["verified_recoveries"] == 1


# =====================================================================
# Ledger
# =====================================================================

class TestLedger:
    """Full audit ledger for steward inspection."""

    def test_ledger_structure(self, adapter):
        adapter.store_turn(
            session_id="s1", turn_number=1,
            prompt="p", response="r",
        )
        ledger = adapter.get_ledger(session_id="s1")

        assert "db_path" in ledger
        assert "total_events" in ledger
        assert "quarantined_events" in ledger
        assert "baseline_window" in ledger
        assert ledger["total_events"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
