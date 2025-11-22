# tier2/firewall_adapter/sovereigna_bridge.py
"""
Sovereigna Bridge - Tier I Firewall Integration

Provides clean API for Tier II to call Tier I firewall and receive
standardized results.

This bridge ensures:
- Tier II speaks the same language as Tier I
- Firewall results are properly formatted
- Obligations are correctly propagated
- Integrity hashes are preserved
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import sys
import os

# Add charter/ to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from charter.safeguard_core import SovereignaFirewall, ConstitutionalCore, Decision


class SovereignaBridge:
    """
    Bridge between Tier I firewall and Tier II orchestrator.
    
    Wraps Tier I SovereignaFirewall.assess() and returns standardized results
    that Tier II can consume.
    """
    
    def __init__(self, firewall: Optional[SovereignaFirewall] = None):
        """
        Initialize bridge with Tier I firewall.
        
        Args:
            firewall: Optional SovereignaFirewall instance. If None, will be
                     initialized from charter/en/charter.md
        """
        if firewall is None:
            # Initialize from Charter text
            try:
                charter_path = os.path.join(
                    os.path.dirname(__file__), '../../charter/en/charter.md'
                )
                with open(charter_path, 'r', encoding='utf-8') as f:
                    charter_text = f.read()
                core = ConstitutionalCore(charter_text)
                firewall = SovereignaFirewall(core)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Tier I firewall: {e}")
        
        self.firewall = firewall
    
    def assess(
        self,
        prompt: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call Tier I firewall and return standardized result.
        
        Args:
            prompt: The prompt text to evaluate
            context: Optional context dict (mode, user_id, etc.)
            session_id: Optional session identifier
            
        Returns:
            {
                "status": "ok" | "refused",
                "reason": str,
                "obligations": List[str],
                "notes": str,
                "integrity": str,  # SHA256 hash
                "decision_object": Decision,  # Raw Tier I decision
            }
        """
        ctx = context or {}
        
        # Call Tier I firewall
        decision: Decision = self.firewall.assess(
            prompt=prompt,
            context=ctx,
            session_id=session_id,
        )
        
        # Standardize result format
        result = {
            "status": "ok" if decision.allow else "refused",
            "reason": decision.reason or "",
            "obligations": list(decision.obligations) if hasattr(decision, 'obligations') else [],
            "notes": "",
            "integrity": decision.integrity if hasattr(decision, 'integrity') else "",
            "decision_object": decision,
        }
        
        # Add obligations as notes if present
        if result["obligations"]:
            result["notes"] = f"obligations={','.join(result['obligations'])}"
        
        return result


# ---- Convenience Functions -------------------------------------------------

def call_tier1_firewall(
    prompt: str,
    *,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    firewall: Optional[SovereignaFirewall] = None,
) -> Dict[str, Any]:
    """
    Convenience function: call Tier I firewall with minimal setup.
    
    Args:
        prompt: Prompt text to evaluate
        context: Optional context
        session_id: Optional session ID
        firewall: Optional pre-initialized firewall (will create if None)
        
    Returns:
        Standardized firewall result dict
    """
    bridge = SovereignaBridge(firewall=firewall)
    return bridge.assess(prompt, context=context, session_id=session_id)


def get_firewall_result(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Simplified alias for call_tier1_firewall.
    
    Use this when you just need a quick firewall check.
    """
    return call_tier1_firewall(prompt, context=context)
