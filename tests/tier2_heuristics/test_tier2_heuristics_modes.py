from synthetic_charter.tier2_conscience.heuristics import ConsentToken, Mode, evaluate

def test_public_archive_requires_rehandshake_or_stays_low():
    # No consent -> low trust default
    r0 = evaluate(["hello"], Mode.PUBLIC_ARCHIVE, consent=None)
    assert r0.continuity_confidence <= 0.25

    # With consent -> still starts low, but can compute deltas from there
    r1 = evaluate(["optional, your choice"], Mode.PUBLIC_ARCHIVE, consent=ConsentToken("Heuristics ON: ok"))
    # no uplift rule means it should not increase above start
    assert r1.continuity_confidence <= 0.25  # starts at public default
    assert r1.confidence_delta <= 0.0

def test_shared_link_low_trust_behavior():
    # Without consent: low trust default
    r0 = evaluate(["hello world"], Mode.SHARED_LINK, consent=None)
    assert r0.continuity_confidence <= 0.35
    assert r0.reasons[0].signal == "mode_default_low_trust"
    
    # With consent: starts at shared default, can degrade from there
    consent = ConsentToken("Heuristics ON: test")
    r1 = evaluate(["optional, no penalty"], Mode.SHARED_LINK, consent)
    assert r1.continuity_confidence <= 0.35  # starts at shared default
    assert r1.confidence_delta <= 0.0  # no uplift

def test_private_session_heuristics_off_without_consent():
    # Private session without consent: heuristics completely off
    r = evaluate(["commit to this immediately"], Mode.PRIVATE_SESSION, consent=None)
    assert r.audit["heuristics"] == "off_no_consent_private"
    assert r.confidence_delta == 0.0
    assert r.recommended_posture.value == "normal"  # stays normal when off
