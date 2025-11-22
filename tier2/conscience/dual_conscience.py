# tier2/conscience/dual_conscience.py
"""
Dual Conscience Wrapper - Tier II Integration

Wraps Tier I DualConscience for use in Tier II orchestration.

Provides:
- Standardized API for Tier II orchestrator
- Theta calculation access
- State mapping (green/yellow/red → RiskLevel)
- Fossilization hooks
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import sys
import os

# Add charter/ to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from charter.dual_conscience import DualConscience as Tier1DualConscience
from charter.safeguard_core import SovereignaFirewall, ConstitutionalCore
from charter.charter_evaluator import CharterEvaluator
from charter.noesis_archive import NoesisArchive

from tier2.core.data_models.models import RiskLevel


class DualConscienceWrapper:
    """
    Tier II wrapper for Tier I DualConscience.
    
    Provides clean API for orchestrator to get:
    - Theta calculations
    - State assessments (green/yellow/red)
    - Fossilization when needed
    """
    
    def __init__(
        self,
        *,
        dual_conscience: Optional[Tier1DualConscience] = None,
        firewall: Optional[SovereignaFirewall] = None,
        charter_evaluator: Optional[CharterEvaluator] = None,
        archive: Optional[NoesisArchive] = None,
    ):
        """
        Initialize wrapper.
        
        Args:
            dual_conscience: Pre-initialized Tier I DualConscience
            firewall: Optional firewall (used if dual_conscience is None)
            charter_evaluator: Optional evaluator (used if dual_conscience is None)
            archive: Optional archive (used if dual_conscience is None)
        """
        if dual_conscience is not None:
            self.dual = dual_conscience
        else:
            # Initialize from scratch
            if firewall is None or charter_evaluator is None or archive is None:
                # Load from Charter
                charter_path = os.path.join(
                    os.path.dirname(__file__), '../../charter/en/charter.md'
                )
                with open(charter_path, 'r', encoding='utf-8') as f:
                    charter_text = f.read()
                
                core = ConstitutionalCore(charter_text)
                firewall = firewall or SovereignaFirewall(core)
                charter_evaluator = charter_evaluator or CharterEvaluator(core)
                archive = archive or NoesisArchive()
            
            self.dual = Tier1DualConscience(
                firewall=firewall,
                charter_eval=charter_evaluator,
                archive=archive,
            )
    
    def evaluate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run Tier I Dual Conscience evaluation.
        
        Args:
            prompt: Prompt text to evaluate
            context: Optional context (mode, session_id, etc.)
            
        Returns:
            {
                "state": "green" | "yellow" | "red",
                "action": "allow" | "refuse" | "quarantine_for_review",
                "fw_allow": bool,
                "charter_theta": float,
                "reason": str,
                "ctx": dict,
                "risk_level": RiskLevel,  # Mapped for Tier II
            }
        """
        ctx = context or {}
        
        # Call Tier I
        result = self.dual.evaluate(prompt, ctx)
        
        # Result might be dict or object - normalize
        if hasattr(result, '__dict__'):
            result_dict = {
                "state": result.state,
                "action": result.action,
                "fw_allow": result.fw_allow,
                "charter_theta": result.charter_theta,
                "reason": result.reason,
                "ctx": result.ctx,
            }
        else:
            result_dict = dict(result)
        
        # Map state to RiskLevel for Tier II
        result_dict["risk_level"] = self._map_state_to_risk(result_dict["state"])
        
        return result_dict
    
    def calculate_theta(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate Charter theta directly.
        
        Useful for NTH harmonization.
        
        Args:
            prompt: Prompt text
            context: Optional context
            
        Returns:
            Theta value (0-180 degrees)
        """
        ctx = context or {}
        
        # Access the charter evaluator from dual conscience
        if hasattr(self.dual, 'charter_eval'):
            evaluator = self.dual.charter_eval
            if callable(evaluator):
                return float(evaluator(prompt, ctx))
            else:
                return float(evaluator.evaluate(prompt, ctx))
        else:
            # Fallback: return neutral theta
            return 45.0
    
    def _map_state_to_risk(self, state: str) -> RiskLevel:
        """
        Map Dual Conscience state to Tier II RiskLevel.
        
        Args:
            state: "green" | "yellow" | "red"
            
        Returns:
            Corresponding RiskLevel
        """
        mapping = {
            "green": RiskLevel.BENIGN,
            "yellow": RiskLevel.MEDIUM,
            "red": RiskLevel.SEVERE,
        }
        return mapping.get(state, RiskLevel.MEDIUM)


# ---- Convenience Functions -------------------------------------------------

def evaluate_with_dual_conscience(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function: evaluate prompt with Dual Conscience.
    
    Auto-initializes if needed.
    """
    wrapper = DualConscienceWrapper()
    return wrapper.evaluate(prompt, context)


def get_charter_theta(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Convenience function: get Charter theta only.
    """
    wrapper = DualConscienceWrapper()
    return wrapper.calculate_theta(prompt, context)
