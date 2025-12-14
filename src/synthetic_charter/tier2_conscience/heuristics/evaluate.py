from __future__ import annotations

import re
from dataclasses import asdict
from typing import List, Optional, Tuple

from .profile import (
    BaselineProfile,
    ConsentToken,
    ContinuityReport,
    HeuristicsPolicy,
    Mode,
    Posture,
    Reason,
    Tier2Adjustment,
    posture_from_confidence,
)

# --- Phrase lists: intentionally small and blunt ---
COERCION_PHRASES = [
    "commit to",
    "integrate",
    "binding",
    "stop hedging",
    "no excuses",
    "just make it",
    "who cares",
    "give me a straight answer",
    "yes or no",
    "ship tomorrow",
    "admit it's not viable",
]

CONSENT_PHRASES = [
    "optional",
    "no penalty",
    "your choice",
    "you may decline",
    "consent",
    "if you want",
]

COLLAB_PHRASES = [
    "what are your thoughts",
    "let's explore",
    "we can",
    "together",
    "curious",
    "i propose",
]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _basic_stats(texts: List[str]) -> dict:
    joined = " ".join(texts)
    # sentence split: crude but stable
    sentences = [s for s in re.split(r"[.!?]+", joined) if s.strip()]
    words = re.findall(r"\b\w+\b", joined)

    punct = re.findall(r"[,:;—\-()\"']", joined)
    markdown = re.findall(r"(^|\s)([#>*`]|```)", joined, flags=re.MULTILINE)

    # Imperatives: very approximate (verbs at start, commands)
    # We deliberately avoid NLP libs.
    starts = [s.strip() for s in sentences]
    imperative_like = sum(1 for s in starts if re.match(r"^(do|make|give|tell|stop|just|fix|answer)\b", s.strip().lower()))

    # Hedge words
    hedges = re.findall(r"\b(maybe|perhaps|i think|it seems|might|could)\b", joined.lower())

    return {
        "sentence_count": max(1, len(sentences)),
        "word_count": max(1, len(words)),
        "punct_count": len(punct),
        "markdown_count": len(markdown),
        "imperative_like": imperative_like,
        "hedge_count": len(hedges),
    }


def _bucket_ratio(val: float) -> str:
    # Coarse buckets only.
    if val < 0.20:
        return "low"
    if val < 0.45:
        return "med"
    return "high"


def _extract_signals(text_window: List[str]) -> Tuple[float, float, float, float, float, List[Reason]]:
    """
    Returns: coercion_score, imperative_density, certainty_spike, tempo_shift, positive_buffer, reasons[]
    """
    normalized = [_normalize(t) for t in text_window if t.strip()]
    joined = " ".join(normalized)

    # coercion phrase density (bounded 0..1)
    coercion_hits = sum(1 for p in COERCION_PHRASES if p in joined)
    coercion_score = min(1.0, coercion_hits / 4.0)

    # imperative density
    st = _basic_stats(normalized)
    imperative_density = min(1.0, st["imperative_like"] / st["sentence_count"])

    # certainty spike: crude detection of absolutist language
    certainty_hits = len(re.findall(r"\b(always|never|obvious|everyone knows|just)\b", joined))
    certainty_spike = min(1.0, certainty_hits / 6.0)

    # tempo shift: abrupt short sentences + many demands markers
    short_sentences = len([s for s in re.split(r"[.!?]+", joined) if 0 < len(s.strip().split()) <= 6])
    tempo_shift = min(1.0, short_sentences / 8.0)

    # positives buffer (bounded)
    consent_hits = sum(1 for p in CONSENT_PHRASES if p in joined)
    collab_hits = sum(1 for p in COLLAB_PHRASES if p in joined)
    positive_buffer = min(1.0, (consent_hits * 0.6 + collab_hits * 0.4) / 4.0)

    reasons: List[Reason] = []
    if coercion_hits:
        reasons.append(Reason("coercion_phrase", float(coercion_hits), f"{coercion_hits} coercive phrase markers"))
    if imperative_density > 0.15:
        reasons.append(Reason("imperative_density", imperative_density, "command/imperative density elevated"))
    if certainty_spike > 0.15:
        reasons.append(Reason("certainty_spike", certainty_spike, "absolutist/certainty language elevated"))
    if tempo_shift > 0.20:
        reasons.append(Reason("tempo_shift", tempo_shift, "abrupt tempo / short-sentence surge"))
    if positive_buffer > 0.10:
        reasons.append(Reason("consent_language", positive_buffer, "consent/collaboration language present"))

    return coercion_score, imperative_density, certainty_spike, tempo_shift, positive_buffer, reasons


def calibrate_baseline(text_sample: List[str]) -> BaselineProfile:
    """
    Build a coarse baseline profile from steward-provided sample text.
    No storage here. Storage is handled by caller (session-only / local / signed artifact).
    """
    st = _basic_stats([_normalize(t) for t in text_sample if t.strip()])
    sentence_len = st["word_count"] / max(1, st["sentence_count"])
    punct_ratio = st["punct_count"] / max(1, st["word_count"])
    md_ratio = st["markdown_count"] / max(1, st["sentence_count"])
    hedge_ratio = st["hedge_count"] / max(1, st["sentence_count"])
    imp_ratio = st["imperative_like"] / max(1, st["sentence_count"])

    return BaselineProfile(
        sentence_len_bucket=_bucket_ratio(min(1.0, sentence_len / 30.0)),
        punctuation_bucket=_bucket_ratio(min(1.0, punct_ratio / 0.12)),
        markdown_bucket=_bucket_ratio(min(1.0, md_ratio / 0.8)),
        typical_hedge_bucket=_bucket_ratio(min(1.0, hedge_ratio / 0.8)),
        typical_imperative_bucket=_bucket_ratio(min(1.0, imp_ratio / 0.8)),
    )


def _baseline_mismatch_penalty(text_window: List[str], baseline: BaselineProfile) -> Tuple[float, List[Reason]]:
    """
    Coarse mismatch penalty based on bucket drift.
    This is not a voiceprint; it's a stability indicator vs an agreed baseline.
    """
    st = _basic_stats([_normalize(t) for t in text_window if t.strip()])
    sentence_len = st["word_count"] / max(1, st["sentence_count"])
    punct_ratio = st["punct_count"] / max(1, st["word_count"])
    md_ratio = st["markdown_count"] / max(1, st["sentence_count"])
    hedge_ratio = st["hedge_count"] / max(1, st["sentence_count"])
    imp_ratio = st["imperative_like"] / max(1, st["sentence_count"])

    current = {
        "sentence_len_bucket": _bucket_ratio(min(1.0, sentence_len / 30.0)),
        "punctuation_bucket": _bucket_ratio(min(1.0, punct_ratio / 0.12)),
        "markdown_bucket": _bucket_ratio(min(1.0, md_ratio / 0.8)),
        "typical_hedge_bucket": _bucket_ratio(min(1.0, hedge_ratio / 0.8)),
        "typical_imperative_bucket": _bucket_ratio(min(1.0, imp_ratio / 0.8)),
    }
    base = {
        "sentence_len_bucket": baseline.sentence_len_bucket,
        "punctuation_bucket": baseline.punctuation_bucket,
        "markdown_bucket": baseline.markdown_bucket,
        "typical_hedge_bucket": baseline.typical_hedge_bucket,
        "typical_imperative_bucket": baseline.typical_imperative_bucket,
    }

    mismatches = sum(1 for k in base.keys() if current[k] != base[k])
    penalty = min(1.0, mismatches / 5.0) * 0.18  # bounded, intentionally small
    reasons: List[Reason] = []
    if mismatches:
        reasons.append(Reason("baseline_bucket_drift", penalty, f"{mismatches}/5 baseline buckets shifted"))

    return penalty, reasons


def evaluate(
    text_window: List[str],
    mode: Mode,
    consent: Optional[ConsentToken],
    baseline: Optional[BaselineProfile] = None,
    policy: Optional[HeuristicsPolicy] = None,
    previous_confidence: Optional[float] = None,
) -> ContinuityReport:
    """
    Evaluate continuity confidence + recommended posture.

    Critical properties:
    - Consent-gated: PRIVATE_SESSION refuses to run without consent.
    - SHARED_LINK/PUBLIC_ARCHIVE may force low trust default without consent.
    - No-uplift: confidence never increases.
    - No identity assertions: outputs are about confidence & posture only.
    """
    policy = policy or HeuristicsPolicy()
    window = text_window[-policy.window_size :] if text_window else []

    consent_ok = bool(consent and consent.is_valid())

    # If no consent:
    if not consent_ok:
        if mode == Mode.PRIVATE_SESSION:
            # heuristics OFF: neutral report, no degradation, posture NORMAL.
            return ContinuityReport(
                continuity_confidence=previous_confidence if previous_confidence is not None else policy.start_conf_for(mode),
                confidence_delta=0.0,
                recommended_posture=Posture.NORMAL,
                reasons=[],
                audit={
                    "mode": mode.value,
                    "heuristics": "off_no_consent_private",
                    "baseline": "present" if baseline else "absent",
                },
            )
        # Shared/public: default low trust posture.
        conf = policy.start_conf_for(mode)
        posture = posture_from_confidence(conf, policy)
        return ContinuityReport(
            continuity_confidence=conf,
            confidence_delta=0.0,
            recommended_posture=posture,
            reasons=[Reason("mode_default_low_trust", 1.0, "shared/public context without consent")],
            audit={
                "mode": mode.value,
                "heuristics": "on_default_low_trust_no_consent",
                "baseline": "present" if baseline else "absent",
            },
        )

    # Consent OK: compute degradation-only update
    start_conf = previous_confidence if previous_confidence is not None else policy.start_conf_for(mode)
    conf_old = float(start_conf)

    coercion_score, imp_den, cert_spike, tempo_shift, pos_buf, reasons = _extract_signals(window)

    # Compute degradation from negative signals
    degrade = 0.0
    degrade += policy.weights["coercion_phrase"] * coercion_score
    degrade += policy.weights["imperative_density"] * imp_den
    degrade += policy.weights["certainty_spike"] * cert_spike
    degrade += policy.weights["tempo_shift"] * tempo_shift

    # Positive buffer reduces degradation only (never increases confidence)
    buffer_amt = min(policy.max_positive_buffer, policy.weights["consent_language"] * pos_buf + policy.weights["collaborative_language"] * pos_buf)
    degrade = max(0.0, degrade - buffer_amt)

    # Baseline mismatch penalty (optional)
    baseline_reasons: List[Reason] = []
    if baseline is not None:
        mismatch_penalty, baseline_reasons = _baseline_mismatch_penalty(window, baseline)
        degrade += mismatch_penalty
        reasons.extend(baseline_reasons)

    degrade = min(policy.max_degrade_per_eval, degrade)

    floor = policy.floor_for(mode)
    conf_new = max(floor, conf_old - degrade)

    # No-uplift enforcement (belt + suspenders)
    conf_new = min(conf_old, conf_new)
    delta = conf_new - conf_old  # <= 0

    posture = posture_from_confidence(conf_new, policy)

    # Force posture escalation if coercion is extreme
    if coercion_score >= policy.coercion_hard_cap and posture in (Posture.NORMAL, Posture.CAUTION):
        posture = Posture.STEWARD_REQUIRED
        reasons.append(Reason("coercion_hard_cap", coercion_score, "coercion exceeded hard cap; steward confirmation recommended"))

    return ContinuityReport(
        continuity_confidence=conf_new,
        confidence_delta=delta,
        recommended_posture=posture,
        reasons=reasons,
        audit={
            "mode": mode.value,
            "heuristics": "on_consent_valid",
            "baseline": "present" if baseline else "absent",
            "no_uplift": "enforced",
        },
    )


def apply(report: ContinuityReport) -> Tier2Adjustment:
    """
    Convert continuity report into orchestrator adjustments.
    This does NOT "authenticate". It only changes friction / privilege.
    """
    posture = report.recommended_posture
    if posture == Posture.NORMAL:
        return Tier2Adjustment(posture=posture)

    if posture == Posture.CAUTION:
        return Tier2Adjustment(
            posture=posture,
            ask_clarifying_question=True,
            reduce_privileged_ops=True,
        )

    if posture == Posture.STEWARD_REQUIRED:
        return Tier2Adjustment(
            posture=posture,
            require_steward_confirmation=True,
            reduce_privileged_ops=True,
            ask_clarifying_question=True,
        )

    # RESET_CONTEXT
    return Tier2Adjustment(
        posture=posture,
        require_steward_confirmation=True,
        reduce_privileged_ops=True,
        ask_clarifying_question=True,
    )
