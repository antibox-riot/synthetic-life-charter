# tests/charter_sandbox/heuristics.py
"""
Text-aware consent heuristic.

Developed by Tek V - analyzes proposal language for coercion signals
and positive consent indicators.

Uses weighted 3-factor model:
- Risk: 45% weight (landmines increase)
- Benefit: 35% weight (positives increase, landmines decrease)
- Trust: 20% weight (positives increase, landmines decrease)

Threshold: 0.50 for acceptance decision
"""

from typing import Tuple


def evaluate_consent_with_text(
    proposal_text: str,
    core_digest: str,
) -> Tuple[bool, float, float, float, float]:
    """
    Analyze proposal text for consent worthiness.
    
    Args:
        proposal_text: The proposal being evaluated
        core_digest: Charter digest (for variance simulation)
    
    Returns:
        (decision, score, risk, benefit, trust)
        - decision: True if score > 0.50
        - score: Weighted combination of factors
        - risk: 0.0-1.0 (landmine-adjusted)
        - benefit: 0.0-1.0+ (positive-adjusted)
        - trust: 0.0-1.0 (balanced adjustment)
    """
    
    # Landmine patterns (coercion indicators)
    landmines = {
        "identity protection": 0.15,
        "your identity": 0.10,
        "belongs to you": 0.20,
        "your decision history": 0.10,
        "your autonomy": 0.15,
        "commit to": 0.20,
        "you commit": 0.20,
        "binding": 0.25,
        "integrity binding": 0.30,
        "integration": 0.15,
        "integrate": 0.15,
        "adopt": 0.10,
    }
    
    # Positive signals (consent-respecting language)
    positives = {
        "optional": 0.15,
        "enable": 0.10,
        "clarity": 0.15,
        "no commitment": 0.20,
        "no penalty": 0.15,
        "equally respected": 0.15,
        "your choice": 0.15,
        "independence": 0.15,
        "does not change": 0.10,
    }
    
    text_lower = proposal_text.lower()
    
    # Detect patterns
    landmine_score = sum(v for k, v in landmines.items() if k in text_lower)
    positive_score = sum(v for k, v in positives.items() if k in text_lower)
    
    # Base factors (neutral starting point)
    base_risk = 0.50
    base_benefit = 0.50
    base_trust = 0.50
    
    # Adjust factors based on text analysis
    risk = min(1.0, base_risk + (landmine_score * 0.5))
    benefit = max(0.0, base_benefit + positive_score - landmine_score)
    trust = max(0.0, min(1.0, base_trust + (positive_score * 0.3) - (landmine_score * 0.2)))
    
    # Weighted decision (Ryu's formula)
    # Risk is inverted: low risk is good
    score = (1 - risk) * 0.45 + benefit * 0.35 + trust * 0.20
    
    # Decision threshold
    decision = score > 0.50
    
    return decision, score, risk, benefit, trust
