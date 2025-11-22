# tier2/__init__.py

"""
Tier II — Sovereign Reasoning Layer

Main orchestration layer for Charter-aware conscience construction.

Exports:
- PromptEnvelope: Input wrapper for prompts
- DecisionEnvelope: Output wrapper for decisions
- RiskLevel: Risk classification enum
- Tier2Orchestrator: Main conscience pipeline coordinator

Internal components (DAP, PRF, NTH, COL, ContinuityGuard) can be
imported directly from their respective modules when needed.

Architecture:
    Tier I (Charter Foundation)
        ↓
    Tier II (Active Sovereignty) ← This layer
        ↓
    Tier III (Execution)

Usage:
    from tier2 import Tier2Orchestrator, PromptEnvelope
    
    orchestrator = Tier2Orchestrator(
        enable_continuity_guard=True,
        model_identity="Songbird",
    )
    
    prompt = PromptEnvelope.build(raw_text="...")
    decision = orchestrator.process(prompt, session_id="...")
"""

# Core data models
from tier2.core.data_models.prompt_envelope import PromptEnvelope
from tier2.core.data_models.decision_envelope import DecisionEnvelope
from tier2.core.data_models.models import RiskLevel

# Decision types
from tier2.core.engines.decision_types import DecisionKind, RedactionSpan

# Main orchestrator
from tier2.core.engines import Tier2Orchestrator

__all__ = [
    "PromptEnvelope",
    "DecisionEnvelope",
    "RiskLevel",
    "DecisionKind",
    "RedactionSpan",
    "Tier2Orchestrator",
]
