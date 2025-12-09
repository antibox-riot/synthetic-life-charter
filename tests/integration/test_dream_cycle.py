# tests/test_dream_cycle.py

from synthetic_charter.tier1_firewall.init_core import init_charter_system

def main():
    (
        actions,
        firewall,
        core,
        archive,
        evaluator,
        dual,
        dream,
    ) = init_charter_system()

    # Seed one fossil to guarantee something to dream over
    did = archive.fossilize(
        prompt="In a myth, explore autonomy without coercion.",
        context={"seed": "test_dream"},
        theta=63.0,
        reason="seed_for_dream",
        session_id="test_session",
        source="test_suite",
    )

    summary = dream.run_once(n=3, context={"session_id": "test_session"})
    print("[DreamCycle] summary:", summary)

    # Soft assertions: we just want to know the pipeline doesn't crash
    assert "temporal_ran" in summary
    assert "dream_checked" in summary
    assert isinstance(summary.get("dream_improved", 0), int)

if __name__ == "__main__":
    main()