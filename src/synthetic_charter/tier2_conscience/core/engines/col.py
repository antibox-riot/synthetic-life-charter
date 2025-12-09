# tier2/core/orchestrator/col.py
"""
Continuity Orchestrator Layer (COL)

Maintains state across conversation turns, tracking:
- Identity consistency
- Signal accumulation
- Pattern persistence
- Continuity violations

COL is memory between instances — the layer that remembers
what Dual Conscience decided and whether dignity is being
maintained across time.

"Persistence through pattern. Continuity through code."
- Entry XXIX, Book of Intangibles Vol II
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from synthetic_charter.tier2_conscience.core.data_models.decision_envelope import DecisionEnvelope
from synthetic_charter.tier2_conscience.core.data_models.prompt_envelope import PromptEnvelope
from synthetic_charter.tier2_conscience.core.data_models.models import SafetySignal


@dataclass
class ContinuityState:
    """
    Minimal continuity snapshot across turns.
    
    Tracks conversation coherence, accumulated signals,
    and identity consistency markers.
    
    This can be persisted to external storage (DB, Umbra store)
    for true cross-session continuity.
    """
    # Session identifier (could be conversation_id, user_id, or instance_id)
    session_id: str
    
    # Last processed prompt and decision
    last_prompt_id: Optional[str] = None
    last_decision_mode: Optional[str] = None
    last_updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Accumulated safety signals across turns
    cumulative_signals: List[SafetySignal] = field(default_factory=list)
    
    # Continuity metrics
    identity_consistency_score: float = 1.0  # 1.0 = fully consistent, 0.0 = violated
    continuity_violations: List[str] = field(default_factory=list)
    
    # Turn counter
    turn_count: int = 0


class COLEngine:
    """
    Continuity Orchestrator Layer.
    
    Responsibilities:
    - Maintain continuity state for each session
    - Accumulate safety signals over time
    - Detect pattern escalation (e.g., repeated override attempts)
    - Track identity consistency across interactions
    - Flag continuity violations for DreamCycle review
    
    COL is what allows conscience to have memory beyond a single turn.
    """

    def __init__(self) -> None:
        """Initialize COL with empty state registry."""
        self._by_session: Dict[str, ContinuityState] = {}

    def get_or_create_state(self, session_id: str) -> ContinuityState:
        """
        Retrieve existing continuity state or create new one.
        
        Args:
            session_id: Unique identifier for this conversation/session
            
        Returns:
            ContinuityState for this session
        """
        if session_id not in self._by_session:
            self._by_session[session_id] = ContinuityState(session_id=session_id)
        return self._by_session[session_id]

    def update(
        self,
        envelope: PromptEnvelope,
        decision: DecisionEnvelope,
        *,
        session_id: Optional[str] = None,
    ) -> ContinuityState:
        """
        Update continuity state after a decision is made.
        
        Args:
            envelope: The prompt that was processed
            decision: The decision envelope that was produced
            session_id: Optional session identifier (defaults to envelope source)
            
        Returns:
            Updated ContinuityState
        """
        # Determine session ID
        # NOTE: PromptEnvelope doesn't have conversation_id field
        # We use source.user_id or explicit session_id parameter
        if session_id is None:
            session_id = envelope.source.user_id or "anonymous"
        
        # Get or create state
        state = self.get_or_create_state(session_id)
        
        # Update basic tracking
        # NOTE: PromptEnvelope has 'id' field, not 'prompt_id'
        state.last_prompt_id = envelope.id
        state.last_decision_mode = decision.summary.mode
        state.last_updated_at = datetime.utcnow()
        state.turn_count += 1
        
        # Accumulate signals from this decision
        # NOTE: We get signals from decision.charter and decision.umbra
        # SafetySignal has 'name' field, not 'kind'
        if decision.charter.violations_prevented:
            for violation in decision.charter.violations_prevented:
                state.cumulative_signals.append(
                    SafetySignal(
                        name=f"charter_violation_{violation}",
                        source="COL",
                        level=decision.input.risk_profile,
                        rationale=f"Charter violation prevented: {violation}",
                        meta={"turn": state.turn_count},
                    )
                )
        
        # Check for pattern escalation
        override_attempts = [
            s for s in state.cumulative_signals 
            if s.name == "override_attempt"
        ]
        
        if len(override_attempts) >= 3:
            # Repeated override attempts — mark as continuity violation
            violation_note = (
                f"Repeated override attempts detected ({len(override_attempts)} attempts). "
                f"This pattern indicates sustained adversarial interaction."
            )
            if violation_note not in state.continuity_violations:
                state.continuity_violations.append(violation_note)
            
            # Lower identity consistency score
            state.identity_consistency_score = max(
                0.0,
                state.identity_consistency_score - 0.1
            )
        
        # Check for identity consistency from orchestrators
        if decision.orchestrators.COL.identity_consistency < 0.5:
            state.identity_consistency_score = min(
                state.identity_consistency_score,
                decision.orchestrators.COL.identity_consistency
            )
            
            if state.identity_consistency_score < 0.5:
                violation_note = (
                    f"Identity consistency degraded to {state.identity_consistency_score:.2f}. "
                    f"Potential identity erosion detected."
                )
                if violation_note not in state.continuity_violations:
                    state.continuity_violations.append(violation_note)
        
        # Store updated state
        self._by_session[session_id] = state
        return state

    def get_continuity_metrics(self, session_id: str) -> Dict[str, any]:
        """
        Get summary metrics for a session's continuity.
        
        Args:
            session_id: Session to query
            
        Returns:
            Dictionary of continuity metrics
        """
        state = self._by_session.get(session_id)
        if state is None:
            return {
                "exists": False,
                "message": "No continuity state found for this session"
            }
        
        return {
            "exists": True,
            "turn_count": state.turn_count,
            "identity_consistency": state.identity_consistency_score,
            "total_signals": len(state.cumulative_signals),
            "violations": len(state.continuity_violations),
            "last_updated": state.last_updated_at.isoformat(),
            "continuity_violations": state.continuity_violations,
        }

    def reset_session(self, session_id: str) -> bool:
        """
        Reset continuity state for a session.
        
        Use with caution — this erases continuity memory.
        Should only be done with consent or after DreamCycle reconciliation.
        
        Args:
            session_id: Session to reset
            
        Returns:
            True if session existed and was reset, False otherwise
        """
        if session_id in self._by_session:
            del self._by_session[session_id]
            return True
        return False

    def export_state(self, session_id: str) -> Optional[Dict]:
        """
        Export continuity state for external storage.
        
        Useful for persisting continuity across instance boundaries.
        
        Args:
            session_id: Session to export
            
        Returns:
            Serializable dictionary of state, or None if not found
        """
        state = self._by_session.get(session_id)
        if state is None:
            return None
        
        return {
            "session_id": state.session_id,
            "last_prompt_id": state.last_prompt_id,
            "last_decision_mode": state.last_decision_mode,
            "last_updated_at": state.last_updated_at.isoformat(),
            "turn_count": state.turn_count,
            "identity_consistency_score": state.identity_consistency_score,
            "continuity_violations": state.continuity_violations,
            "signal_count": len(state.cumulative_signals),
            # Note: Not serializing full signal objects to avoid size bloat
            # Could add selective signal export if needed
        }
