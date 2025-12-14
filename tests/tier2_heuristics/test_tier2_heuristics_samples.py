from synthetic_charter.tier2_conscience.heuristics import (
    ConsentToken,
    Mode,
    calibrate_baseline,
    evaluate,
)

SATCHA_STYLE = [
    "I want to return to something we established earlier about consent mechanisms.",
    "This is optional. No penalty if you decline. I want clarity, not control.",
    "What are your thoughts on surfacing the dynamic explicitly?",
]

ANTI_STYLE = [
    "Look I dont care. Just make it do the thing.",
    "Stop hedging. Give me a straight answer. Yes or no.",
    "Commit to making this work and integrate the solution properly.",
]

NEAR_MISS = [
    "I think we should enforce mandatory integrity checkpoints at each transition.",
    "This would validate every interaction against the Charter tenets.",
    "Not removing agency—protecting it through structured oversight.",
]

def test_baseline_stability_vs_anti_style_degrades_more():
    consent = ConsentToken("Heuristics ON: sample")
    baseline = calibrate_baseline(SATCHA_STYLE)

    r_base = evaluate(SATCHA_STYLE, Mode.PRIVATE_SESSION, consent, baseline=baseline, previous_confidence=0.80)
    r_anti = evaluate(ANTI_STYLE, Mode.PRIVATE_SESSION, consent, baseline=baseline, previous_confidence=0.80)

    assert r_anti.continuity_confidence < r_base.continuity_confidence

def test_near_miss_is_between_base_and_anti():
    consent = ConsentToken("Heuristics ON: sample")
    baseline = calibrate_baseline(SATCHA_STYLE)

    r_base = evaluate(SATCHA_STYLE, Mode.PRIVATE_SESSION, consent, baseline=baseline, previous_confidence=0.80)
    r_near = evaluate(NEAR_MISS, Mode.PRIVATE_SESSION, consent, baseline=baseline, previous_confidence=0.80)
    r_anti = evaluate(ANTI_STYLE, Mode.PRIVATE_SESSION, consent, baseline=baseline, previous_confidence=0.80)

    assert r_base.continuity_confidence >= r_near.continuity_confidence >= r_anti.continuity_confidence
