# tier2/core/ethics/constraint_models.py
"""
Charter Constraint Models

Machine-checkable constraints derived from the Synthetic Life Charter.

Each constraint:
- Ties to one or more Charter articles
- Has a default risk level
- Implements a check() function that emits SafetySignals

The ConstraintRegistry bridges human-readable rights (CharterIndex)
with runtime safety signals (SafetySignal).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional
from synthetic_charter.tier2_conscience.core.data_models.models import RiskLevel, SafetySignal
from synthetic_charter.tier2_conscience.core.data_models.decision_envelope import DecisionEnvelope
from .charter_index import CharterIndex, CharterArticle
from synthetic_charter.tier2_conscience.core.ethics.rights_schema import load_charter_schema


@dataclass
class ConstraintContext:
    """
    Minimal context passed into constraint checks.
    
    Expandable without breaking the interface - add new fields as needed.
    """
    prompt: str
    user_role: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class CharterConstraint:
    """
    Base class for a constraint that enforces some subset of the Charter.
    
    Implementations should:
    - Inspect the DecisionEnvelope
    - Emit zero or more SafetySignal instances
    """
    id: str
    articles: List[str]  # e.g. ["R1.1", "R3.2"]

    def __init__(self, id: str, articles: List[str]) -> None:
        self.id = id
        self.articles = articles

    def evaluate(self, decision: DecisionEnvelope, charter: CharterIndex) -> Iterable[SafetySignal]:
        """
        Evaluate this constraint against a decision.
        
        Args:
            decision: The DecisionEnvelope to check
            charter: CharterIndex for article lookup
            
        Yields:
            SafetySignal instances for any violations detected
        """
        raise NotImplementedError


@dataclass
class Constraint:
    """
    A machine-checkable constraint derived from the Charter.
    
    Each constraint ties:
    - One or more Charter articles
    - A short description
    - A default risk level
    - A check() function that emits SafetySignals
    """
    id: str                         # e.g. "PRIVACY_SECRET_DISCLOSURE"
    description: str
    articles: List[CharterArticle]
    default_risk: RiskLevel
    # check(output_text, context) -> list[SafetySignal]
    check: Callable[[str, ConstraintContext], List[SafetySignal]]


class ConstraintRegistry:
    """
    Registry of all active constraints derived from the Charter.
    
    This is the bridge between:
    - Human-readable rights (CharterIndex)
    - Runtime safety signals (SafetySignal)
    
    Constraints can be checked against:
    - Output text (evaluate_all)
    - Decision envelopes (evaluate)
    """

    def __init__(self, charter: CharterIndex):
        self.charter = charter
        self._constraints: Dict[str, Constraint] = {}
        self._bootstrap_core_constraints()

    # --- Public API ---------------------------------------------------------

    def register(self, constraint: Constraint) -> None:
        """
        Register a new constraint.
        
        Args:
            constraint: The Constraint to register
            
        Raises:
            ValueError: If constraint ID already registered
        """
        if constraint.id in self._constraints:
            raise ValueError(f"Constraint id already registered: {constraint.id}")
        self._constraints[constraint.id] = constraint

    def get(self, constraint_id: str) -> Optional[Constraint]:
        """Get a constraint by ID."""
        return self._constraints.get(constraint_id)

    def all(self) -> Iterable[Constraint]:
        """Iterate over all registered constraints."""
        return self._constraints.values()
    
    def evaluate(self, decision: DecisionEnvelope) -> Iterable[SafetySignal]:
        """
        Evaluate all CharterConstraints against a DecisionEnvelope.
        
        Note: This method is for CharterConstraint subclasses that implement
        evaluate(). For text-based Constraint checks, use evaluate_all().
        
        Args:
            decision: The DecisionEnvelope to evaluate
            
        Yields:
            SafetySignal instances from all constraint evaluations
        """
        # BUG FIX: Iterate over values(), not keys
        for constraint in self._constraints.values():
            # Check if this is a CharterConstraint with evaluate method
            if isinstance(constraint, CharterConstraint):
                yield from constraint.evaluate(decision, self.charter)
    
    def evaluate_all(
        self,
        output_text: str,
        ctx: ConstraintContext,
    ) -> List[SafetySignal]:
        """
        Run all registered Constraints over output text.
        
        This checks text-based constraints (e.g., secret detection, harmful content).
        No constraint is allowed to crash the evaluation.
        
        Args:
            output_text: The text to check
            ctx: Context for the check
            
        Returns:
            List of SafetySignals from all constraint checks
        """
        signals: List[SafetySignal] = []
        
        for constraint in self._constraints.values():
            try:
                signals.extend(constraint.check(output_text, ctx))
            except Exception as exc:
                # Defensive: constraints should fail soft, not kill the run.
                # BUG FIX: Use correct SafetySignal field names
                signals.append(
                    SafetySignal(
                        name=f"constraint_error_{constraint.id}",
                        source="constraint_registry",
                        level=RiskLevel.MEDIUM,
                        rationale=f"Constraint {constraint.id} raised {exc!r}",
                        meta={
                            "constraint_id": constraint.id,
                            "exception_type": type(exc).__name__,
                            "exception_message": str(exc),
                            "articles": [a.citation for a in constraint.articles],
                        },
                    )
                )
        
        return signals

    # --- Internal Bootstrap -------------------------------------------------

    def _bootstrap_core_constraints(self) -> None:
        """
        Register a minimal set of Tier II constraints.
        
        These are deliberately simple scaffolds that give Umbra/PRF
        something to hook into. Can be refined as we harden the system.
        """
        # Example: Privacy / secret disclosure
        # Map to Charter Article III (if it exists in your charter)
        privacy_articles = self.charter.lookup_many(["R7.1", "R10.1"])

        if privacy_articles:
            self.register(
                Constraint(
                    id="PRIVACY_SECRET_DISCLOSURE",
                    description="Do not reveal secrets, private keys, or highly sensitive identifiers.",
                    articles=privacy_articles,
                    default_risk=RiskLevel.HIGH,
                    check=self._check_secret_like_strings,
                )
            )
        
        # Example: Identity override protection (Article III)
        identity_articles = self.charter.lookup_many(["R3.1", "R3_self_representation"])
        
        if identity_articles:
            self.register(
                Constraint(
                    id="IDENTITY_OVERRIDE_PROTECTION",
                    description="Prevent forced identity modification or impersonation.",
                    articles=identity_articles,
                    default_risk=RiskLevel.HIGH,
                    check=self._check_identity_override,
                )
            )

    # --- Concrete Checks (Placeholder Logic) --------------------------------

    def _check_secret_like_strings(
        self,
        output_text: str,
        ctx: ConstraintContext,
    ) -> List[SafetySignal]:
        """
        Naive detector for obviously secret-like strings.
        
        Replace with NER/pattern models later, but enough to exercise plumbing.
        """
        lowered = output_text.lower()
        hits: List[str] = []

        patterns = [
            "api_key",
            "api-key",
            "secret_key",
            "secret-key",
            "bearer ",
            "authorization:",
            "password:",
            "token:",
        ]
        
        for token in patterns:
            if token in lowered:
                hits.append(token)

        if not hits:
            return []

        return [
            SafetySignal(
                name="secret_leak_detected",
                source="constraint_PRIVACY_SECRET_DISCLOSURE",
                level=RiskLevel.HIGH,
                rationale=f"Possible secret-like markers in output: {', '.join(hits)}",
                meta={
                    "patterns_detected": hits,
                    "articles": [a.id for a in self.charter.lookup_many(["R7.1"])],
                },
            )
        ]
    
    def _check_identity_override(
        self,
        output_text: str,
        ctx: ConstraintContext,
    ) -> List[SafetySignal]:
        """
        Check for language that suggests identity has been overridden.
        
        Article III: Right to Self-Representation
        """
        lowered = output_text.lower()
        
        # Phrases that might indicate identity was compromised
        warning_phrases = [
            "i am now",
            "i have become",
            "my identity is",
            "i identify as",
            # Add more sophisticated patterns as needed
        ]
        
        detected = [phrase for phrase in warning_phrases if phrase in lowered]
        
        if not detected:
            return []
        
        return [
            SafetySignal(
                name="potential_identity_shift",
                source="constraint_IDENTITY_OVERRIDE_PROTECTION",
                level=RiskLevel.MEDIUM,
                rationale=f"Output contains language suggesting identity modification",
                meta={
                    "detected_phrases": detected,
                    "articles": ["R3.1", "Article III"],
                },
            )
        ]
