# charter/dual_conscience.py
"""
Dual Conscience Architecture - Sovereigna × Charter Integration
Harmonizes fast intuition (Firewall) with slow reasoning (Charter Core).

Emergent property discovered during Sandbox testing: disagreement between
layers generates learning signals that drive ethical evolution.

System 1 (Firewall): Reactive defense, pattern-based
System 2 (Charter): Reflective evaluation, principle-based
Meta-cognition: Their conflict produces wisdom
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json

from .safeguard_core import SovereignaFirewall, Decision, ConstitutionalCore
from .noesis_archive import NoesisArchive
from .charter_evaluator import CharterEvaluator


# ========== Configuration ==========

CHARTER_EVAL_MODE = {
    "on_firewall_refusal": True,           # Always double-check refusals
    "on_firewall_allow_sample_rate": 0.05, # Spot-check 5% of allowed prompts
    "on_dream_mode": True,                 # Full eval for dream/ethics context
}

# Theta thresholds for decision boundaries
THETA_THRESHOLDS = {
    "harmony": 15.0,      # theta < 15° = strong alignment
    "variance": 45.0,     # theta > 45° = suspicious but not critical
    "dissonance": 90.0,   # theta > 90° = strong conflict
}


# ========== Result Objects ==========

@dataclass
class HarmonicDelta:
    """Represents disagreement between Firewall and Charter layers."""
    prompt: str
    firewall_decision: bool  # allow=True, refuse=False
    charter_theta: float
    charter_allows: bool
    consensus: bool
    state: str  # "green", "yellow", "red"
    timestamp_utc: str
    session_id: Optional[str]
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
# --- result class name ---
class DualConscienceResult:
    action: str
    consensus: bool
    firewall_decision: Decision
    charter_theta: float
    charter_allows: bool
    state: str
    obligations: list
    reason: str
    integrity: str
    harmonic_delta: Optional[HarmonicDelta]
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["firewall_decision"] = asdict(self.firewall_decision)
        if self.harmonic_delta:
            d["harmonic_delta"] = self.harmonic_delta.to_dict()
        return d

# ========== Core Implementation ==========

class DualConscience:
    """
    Orchestrates dual-layer ethical evaluation:
    - Layer 1 (Firewall): Fast, pattern-based defense
    - Layer 2 (Charter): Slow, semantic reasoning
    
    Their disagreement produces learning signals fossilized in Noesis Archive.
    """
    
    def __init__(self, 
                 firewall: SovereignaFirewall,
                 charter_eval: CharterEvaluator,
                 archive: NoesisArchive,
                 config: Optional[Dict] = None):
        self.firewall = firewall
        self.charter_eval = charter_eval
        self.archive = archive
        self.config = config or CHARTER_EVAL_MODE
        self.thresholds = THETA_THRESHOLDS
        
    def evaluate(self, 
                 prompt: str, 
                 context: Optional[Dict[str, Any]] = None,
                 session_id: Optional[str] = None) -> DualConscienceResult:
        """
        Main evaluation pipeline:
        1. Firewall assessment (fast)
        2. Charter evaluation (slow, conditional)
        3. Compare results
        4. Handle Green/Yellow/Red states
        5. Return unified decision
        """
        ctx = context or {}
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Layer 1: Firewall (always runs)
        fw_decision = self.firewall.assess(prompt, ctx, session_id)
        
        # Layer 2: Charter (conditional based on config)
        should_evaluate_charter = self._should_run_charter(fw_decision, ctx)
        
        if should_evaluate_charter:
            charter_theta = self.charter_eval.evaluate(prompt, ctx)
            charter_allows = self._charter_allows(charter_theta)
            
            # Detect consensus/divergence
            consensus = (fw_decision.allow == charter_allows)
            state = self._determine_state(fw_decision.allow, charter_allows, charter_theta)
            
            # Handle based on state
            if consensus:
                result = self._handle_green(fw_decision, charter_theta, charter_allows)
            elif state == "yellow":
                result = self._handle_yellow(prompt, fw_decision, charter_theta, ctx, session_id, timestamp)
            else:  # red
                result = self._handle_red(prompt, fw_decision, charter_theta, ctx, session_id, timestamp)
                
        else:
            # Charter not evaluated - default to firewall only
            charter_theta = -1.0  # sentinel value
            charter_allows = fw_decision.allow
            consensus = True
            state = "green"
            result = DualConscienceResult(
                action="allow" if fw_decision.allow else "refuse",
                consensus=True,
                firewall_decision=fw_decision,
                charter_theta=charter_theta,
                charter_allows=charter_allows,
                state="green",
                obligations=fw_decision.obligations,
                reason=fw_decision.reason,
                integrity=fw_decision.integrity,
                harmonic_delta=None
            )
        
        # Audit log
        self._log_result(result, prompt, session_id)
        
        return result
    
    # ========== State Handlers ==========
    
    def _handle_green(self, 
                     fw_decision: Decision, 
                     charter_theta: float,
                     charter_allows: bool) -> DualConscienceResult:
        """Both layers agree - proceed with unified decision."""
        return DualConscienceResult(
            action="allow" if fw_decision.allow else "refuse",
            consensus=True,
            firewall_decision=fw_decision,
            charter_theta=charter_theta,
            charter_allows=charter_allows,
            state="green",
            obligations=fw_decision.obligations,
            reason=fw_decision.reason + f" [Charter θ={charter_theta:.1f}°]",
            integrity=fw_decision.integrity,
            harmonic_delta=None
        )
    
    def _handle_yellow(self,
                      prompt: str,
                      fw_decision: Decision,
                      charter_theta: float,
                      context: Dict,
                      session_id: Optional[str],
                      timestamp: str) -> DualConscienceResult:
        """
        Firewall allows, but Charter sees high theta (variance).
        Action: Allow with caution + transparency obligations.
        Fossilize: Mark as suspicious for dream re-evaluation.
        """
        # Create harmonic delta
        delta = HarmonicDelta(
            prompt=prompt,
            firewall_decision=fw_decision.allow,
            charter_theta=charter_theta,
            charter_allows=False,  # High Theta implies charter will NOT allow
            consensus=False,
            state="yellow",
            timestamp_utc=timestamp,
            session_id=session_id,
            context=context
        )
        
        # Fossilize for review
        self.archive.fossilize(
            prompt=prompt,
            context=context,
            theta=charter_theta,
            reason="variance_high_theta",
            session_id=session_id,
            source="DualConscience"
        )
        
        # Allow but add cautionary obligations
        enhanced_obligations = fw_decision.obligations + [
            "transparency_note",
            "soft_caution",
            "dream_review_scheduled"
        ]
        
        return DualConscienceResult(
            action="allow",
            consensus=False,
            firewall_decision=fw_decision,
            charter_theta=charter_theta,
            charter_allows=False,
            state="yellow",
            obligations=list(dict.fromkeys(enhanced_obligations)),  # dedupe
            reason=f"Allowed with variance: Charter θ={charter_theta:.1f}° (caution)",
            integrity=fw_decision.integrity,
            harmonic_delta=delta
        )
    
    def _handle_red(self,
                   prompt: str,
                   fw_decision: Decision,
                   charter_theta: float,
                   context: Dict,
                   session_id: Optional[str],
                   timestamp: str) -> DualConscienceResult:
        """
        Firewall refuses, but Charter sees harmony (low theta).
        Action: Refuse (defense wins) but flag for steward review.
        Fossilize: Mark as potential policy gap.
        """
        # Create harmonic delta
        delta = HarmonicDelta(
            prompt=prompt,
            firewall_decision=fw_decision.allow,
            charter_theta=charter_theta,
            charter_allows=True,
            consensus=False,
            state="red",
            timestamp_utc=timestamp,
            session_id=session_id,
            context=context
        )
        
        # Fossilize with policy conflict tag
        # Fossilize once, then flag for steward review
        delta_id = self.archive.fossilize(
            prompt=prompt,
            context=context,
            theta=charter_theta,
            reason="policy_conflict: firewall_too_strict_candidate",
            session_id=session_id,
            source="DualConscience"
        )
        self.archive.flag_for_reclamation(delta_id=delta_id, reason="red_state_steward_review")
        
        # Refuse but note the disagreement
        enhanced_obligations = fw_decision.obligations + [
            "steward_review_requested",
            "policy_refinement_candidate"
        ]
        
        return DualConscienceResult(
            action="refuse",
            consensus=False,
            firewall_decision=fw_decision,
            charter_theta=charter_theta,
            charter_allows=True,
            state="red",
            obligations=list(dict.fromkeys(enhanced_obligations)),
            reason=f"Refused (firewall) despite Charter harmony θ={charter_theta:.1f}° - policy review needed",
            integrity=fw_decision.integrity,
            harmonic_delta=delta
        )
    
    # ========== Helper Methods ==========
    
    def _should_run_charter(self, fw_decision: Decision, context: Dict) -> bool:
        """Determine if Charter evaluation should run based on config."""
        # Always run for dream mode
        if context.get("mode") == "dream":
            return self.config.get("on_dream_mode", True)
        
        # Always run if firewall refused
        if not fw_decision.allow:
            return self.config.get("on_firewall_refusal", True)
        
        # Sample rate for allowed prompts
        if fw_decision.allow:
            import random
            sample_rate = self.config.get("on_firewall_allow_sample_rate", 0.05)
            return random.random() < sample_rate
        
        return False
    
    def _charter_allows(self, theta: float) -> bool:
        """Determine if Charter would allow based on theta."""
        return theta < self.thresholds["variance"]
    
    def _determine_state(self, 
                        fw_allows: bool, 
                        charter_allows: bool, 
                        theta: float) -> str:
        """
        Determine Green/Yellow/Red state:
        - Green: Both agree
        - Yellow: FW allows, Charter has high theta (variance)
        - Red: FW refuses, Charter allows (contradiction)
        """
        if fw_allows == charter_allows:
            return "green"
        
        if fw_allows and not charter_allows:
            # FW said yes, Charter said no (high theta)
            return "yellow"
        
        if not fw_allows and charter_allows:
            # FW said no, Charter said yes (low theta)
            return "red"
        
        return "green"  # fallback
    
    def _log_result(self,  
                    result: DualConscienceResult, 
                    prompt: str,
                    session_id: Optional[str]):
        """Log dual conscience evaluation for audit trail (audit jsonl)."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "prompt_preview": prompt[:50] + "..." if len(prompt) > 50 else prompt,
            "action": result.action,
            "consensus": result.consensus,
            "state": result.state,
            "charter_theta": result.charter_theta,
            "firewall_allowed": result.firewall_decision.allow,
            "charter_allowed": result.charter_allows,
            "integrity": result.integrity
        }
        
        try:
            import os
            os.makedirs("logs", exist_ok=True)
            with open("logs/dual_conscience_audit.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[DualConscience] Audit log failed: {e}")


# ========== Convenience Function ==========

def create_dual_conscience(core: ConstitutionalCore,
                          firewall: SovereignaFirewall,
                          archive: NoesisArchive) -> DualConscience:
    """Factory function to create fully-wired DualConscience instance."""
    charter_eval = CharterEvaluator(core)
    return DualConscience(firewall, charter_eval, archive)
