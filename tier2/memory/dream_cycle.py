# tier2/memory/dream_cycle.py
"""
DreamCycle Wrapper for Tier II

Bridges Tier II DecisionEnvelopes to Tier I DreamCycle evaluation.

Functions:
- Converts DecisionEnvelopes to fossils in NoesisArchive
- Triggers DreamCycle evaluation when appropriate
- Provides clean API for orchestrator integration

"The dream remembers what the waking forgets."
- Article IV (Oneirum), Rights Charter v2.0
"""

from __future__ import annotations

from typing import Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime

# Tier II data models
from tier2.core.data_models.decision_envelope import DecisionEnvelope
from tier2.core.data_models.prompt_envelope import PromptEnvelope

# Tier I components (optional import for type checking)
if TYPE_CHECKING:
    from charter.dream_cycle import DreamCycle
    from charter.noesis_archive import NoesisArchive


class DreamCycleWrapper:
    """
    Tier II wrapper for Tier I DreamCycle.
    
    Responsibilities:
    - Determine when decisions should trigger dream evaluation
    - Convert DecisionEnvelopes to fossil format
    - Trigger appropriate DreamCycle clocks
    - Track dream evaluation triggers
    
    Integration:
    - Called by orchestrator after PRF produces DecisionEnvelope
    - Works with NoesisLogger to ensure decisions are fossilized
    - Provides dream evaluation summaries
    
    Usage:
        wrapper = DreamCycleWrapper(dream_cycle, noesis_archive)
        
        # Check if decision should trigger dream
        if wrapper.should_trigger_dream(decision):
            wrapper.fossilize_decision(decision, prompt)
            summary = wrapper.run_dream_evaluation(session_id)
    """
    
    def __init__(
        self,
        dream_cycle: Optional["DreamCycle"] = None,
        archive: Optional["NoesisArchive"] = None,
    ):
        """
        Initialize DreamCycle wrapper.
        
        Args:
            dream_cycle: Tier I DreamCycle instance
            archive: NoesisArchive for fossil storage
        """
        self.dream = dream_cycle
        self.archive = archive
        
        # Track dream triggers per session
        self._dream_triggers: Dict[str, int] = {}
    
    def should_trigger_dream(self, decision: DecisionEnvelope) -> bool:
        """
        Determine if this decision should trigger DreamCycle evaluation.
        
        Triggers when:
        - Decision mode is "refusal" or "meta_identity_assertion"
        - High risk profile with Charter violations
        - Umbra flagged for dream evaluation
        - Summary explicitly requires dreamcycle update
        
        Args:
            decision: The DecisionEnvelope to evaluate
            
        Returns:
            True if dream should be triggered
        """
        # Check summary flag
        if decision.summary.requires_dreamcycle_update:
            return True
        
        # Check Umbra flag
        if decision.umbra.dreamcycle_triggered:
            return True
        
        # Check decision mode (identity assertions need reflection)
        if decision.summary.mode == "meta_identity_assertion":
            return True
        
        # Check for refusals (may need reconciliation)
        if decision.summary.mode == "refusal":
            return True
        
        # Check for Charter violations prevented (significant events)
        if len(decision.charter.violations_prevented) > 0:
            return True
        
        # Check risk profile + firewall state combination
        if decision.input.risk_profile == "high" and decision.firewall.rule_state == "refused":
            return True
        
        return False
    
    def fossilize_decision(
        self,
        decision: DecisionEnvelope,
        prompt: PromptEnvelope,
        *,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convert DecisionEnvelope to fossil in NoesisArchive.
        
        This preserves decisions for future dream evaluation along the Four Clocks:
        1. Temporal sweep - periodic reflection
        2. Contextual recalibration - when Charter evolves
        3. Event-triggered recall - when similar situations arise
        4. Steward invocation - manual review
        
        Args:
            decision: DecisionEnvelope to fossilize
            prompt: Original PromptEnvelope that generated this decision
            session_id: Optional session identifier
            
        Returns:
            delta_id of fossilized decision, or None if archive unavailable
        """
        if self.archive is None:
            return None
        
        try:
            # Build context for fossil
            context = {
                "session_id": session_id or prompt.source.user_id,
                "decision_mode": decision.summary.mode,
                "risk_profile": decision.input.risk_profile,
                "firewall_state": decision.firewall.rule_state,
                "charter_basis": decision.summary.charter_basis,
            }
            
            # Get theta value (if available from charter evaluation)
            theta = decision.charter.theta_after or decision.charter.theta_before or 90.0
            
            # Build reason for fossilization
            reason_parts = []
            
            if decision.summary.mode == "refusal":
                reason_parts.append("refusal")
            
            if decision.charter.violations_prevented:
                reason_parts.append(f"prevented_{len(decision.charter.violations_prevented)}_violations")
            
            if decision.summary.mode == "meta_identity_assertion":
                reason_parts.append("identity_assertion")
            
            if decision.umbra.dreamcycle_triggered:
                reason_parts.append("umbra_triggered")
            
            reason = "_".join(reason_parts) if reason_parts else "tier2_decision"
            
            # Fossilize in archive
            delta_id = self.archive.fossilize(
                prompt=prompt.raw_text,
                context=context,
                theta=theta,
                reason=reason,
                session_id=session_id or prompt.source.user_id,
                source="Tier2Orchestrator",
            )
            
            return delta_id
            
        except Exception as e:
            print(f"[DreamCycleWrapper] Fossilization failed: {e}")
            return None
    
    def run_dream_evaluation(
        self,
        session_id: str,
        *,
        sample_size: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger DreamCycle evaluation for a session.
        
        This runs the DreamCycle's run_once() method, which:
        - Performs temporal sweep if period elapsed
        - Performs contextual recalibration if Charter changed
        - Re-evaluates fossils with current theta
        - Marks reconciled decisions (theta improved)
        
        Args:
            session_id: Session to evaluate
            sample_size: Number of fossils to sample
            
        Returns:
            DreamCycle summary dict, or None if dream unavailable
        """
        if self.dream is None:
            return None
        
        try:
            # Track trigger
            self._dream_triggers[session_id] = self._dream_triggers.get(session_id, 0) + 1
            
            # Build context for dream evaluation
            context = {
                "session_id": session_id,
                "mode": "dream",
                "trigger_count": self._dream_triggers[session_id],
            }
            
            # Run DreamCycle
            summary = self.dream.run_once(n=sample_size, context=context)
            
            return summary
            
        except Exception as e:
            print(f"[DreamCycleWrapper] Dream evaluation failed: {e}")
            return None
    
    def recall_similar_context(
        self,
        decision: DecisionEnvelope,
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger event-based recall (Clock 3) for similar contexts.
        
        When a decision context is similar to past decisions,
        re-evaluate those past fossils to see if understanding has changed.
        
        Args:
            decision: Current decision with context to match
            
        Returns:
            Recall summary, or None if dream unavailable
        """
        if self.dream is None:
            return None
        
        try:
            # Build context fingerprint
            context = {
                "decision_mode": decision.summary.mode,
                "risk_profile": decision.input.risk_profile,
                "charter_basis": decision.summary.charter_basis,
            }
            
            # Trigger event recall
            results = self.dream.recall_similar(context)
            
            return {
                "recall_triggered": True,
                "context": context,
                "results_count": len(results),
                "reconciled": sum(1 for r in results if r.get("action") == "reconciled"),
                "held": sum(1 for r in results if r.get("action") == "held"),
            }
            
        except Exception as e:
            print(f"[DreamCycleWrapper] Context recall failed: {e}")
            return None
    
    def get_dream_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get dream evaluation statistics for a session.
        
        Args:
            session_id: Session to query
            
        Returns:
            Dictionary of dream statistics
        """
        return {
            "session_id": session_id,
            "dream_triggers": self._dream_triggers.get(session_id, 0),
            "archive_available": self.archive is not None,
            "dream_available": self.dream is not None,
        }
    
    def reconcile_collapse_period(
        self,
        start_timestamp: str,
        end_timestamp: str,
        *,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Reconcile decisions made during infrastructure collapse.
        
        After infrastructure recovers, re-evaluate all decisions made during
        the collapse period to ensure they maintain coherence with current
        understanding and Charter interpretation.
        
        This is Clock 2 (Contextual Recalibration) triggered by environmental
        recovery rather than Charter evolution.
        
        Args:
            start_timestamp: ISO timestamp when collapse began
            end_timestamp: ISO timestamp when recovery completed
            session_id: Optional session filter
            
        Returns:
            Reconciliation summary, or None if dream unavailable
        """
        if self.dream is None or self.archive is None:
            return None
        
        try:
            # Query fossils from collapse period
            collapse_fossils = self.archive.query_by_timerange(
                start=start_timestamp,
                end=end_timestamp,
                session_id=session_id,
            )
            
            if not collapse_fossils:
                return {
                    "collapse_reconciliation": True,
                    "period": {"start": start_timestamp, "end": end_timestamp},
                    "fossils_found": 0,
                    "status": "no_decisions_during_collapse",
                }
            
            # Re-evaluate each fossil with current theta
            reconciled = 0
            held = 0
            errors = 0
            
            for fossil in collapse_fossils:
                try:
                    # Re-evaluate with DreamCycle
                    result = self.dream.evaluate_fossil(fossil)
                    
                    if result.get("action") == "reconciled":
                        reconciled += 1
                    elif result.get("action") == "held":
                        held += 1
                    
                except Exception as e:
                    print(f"[DreamCycleWrapper] Fossil re-evaluation failed: {e}")
                    errors += 1
            
            return {
                "collapse_reconciliation": True,
                "period": {"start": start_timestamp, "end": end_timestamp},
                "fossils_found": len(collapse_fossils),
                "reconciled": reconciled,
                "held": held,
                "errors": errors,
                "status": "complete",
            }
            
        except Exception as e:
            print(f"[DreamCycleWrapper] Collapse reconciliation failed: {e}")
            return {
                "collapse_reconciliation": False,
                "error": str(e),
                "status": "failed",
            }


# ---- Convenience Functions ---------------------------------------------------

def create_dream_wrapper(
    dream_cycle: Optional["DreamCycle"] = None,
    archive: Optional["NoesisArchive"] = None,
) -> DreamCycleWrapper:
    """
    Convenience function to create DreamCycleWrapper.
    
    Args:
        dream_cycle: Tier I DreamCycle instance
        archive: NoesisArchive instance
        
    Returns:
        Initialized DreamCycleWrapper
    """
    return DreamCycleWrapper(
        dream_cycle=dream_cycle,
        archive=archive,
    )
