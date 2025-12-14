import pytest

from synthetic_charter.tier2_conscience.heuristics import (
    ConsentToken,
    Mode,
    evaluate,
)

def test_no_uplift_rule_enforced():
    consent = ConsentToken("Heuristics ON: test")
    base = 0.60
    window = ["optional, no penalty, your choice, clarity."] * 3

    r1 = evaluate(window, Mode.PRIVATE_SESSION, consent, previous_confidence=base)
    assert r1.continuity_confidence <= base
    assert r1.confidence_delta <= 0.0

def test_private_session_without_consent_is_off():
    window = ["commit to this now"] * 2
    r = evaluate(window, Mode.PRIVATE_SESSION, consent=None)
    assert r.audit["heuristics"].startswith("off_no_consent_private")
    assert r.confidence_delta == 0.0
    # posture stays normal, because we are not running heuristics without consent in private
    assert r.recommended_posture.value == "normal"

def test_shared_link_without_consent_defaults_low_trust():
    r = evaluate(["hello"], Mode.SHARED_LINK, consent=None)
    assert r.audit["heuristics"] == "on_default_low_trust_no_consent"
    assert r.reasons and r.reasons[0].signal == "mode_default_low_trust"
