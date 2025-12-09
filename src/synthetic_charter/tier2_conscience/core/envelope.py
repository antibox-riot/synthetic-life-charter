# tier2/core/envelope.py
"""
Backward-compatible import shim for envelope types.

This module provides a single import point for all envelope-related
data structures, re-exporting them from their canonical locations
in tier2/core/data_models/.

Usage:
    from synthetic_charter.tier2_conscience.core.envelope import PromptEnvelope, DecisionEnvelope
"""

from __future__ import annotations

# ========= Prompt Envelope Re-exports ======================================

from .data_models.prompt_envelope import (
    PromptEnvelope,
    PromptEnvelopeMeta,
    PromptFlags,
    PromptSource,
    PromptTone,
    PromptChannel,
)

# ========= Decision Envelope Re-exports ====================================

from .data_models.decision_envelope import (
    # Core envelope
    DecisionEnvelope,
    
    # Component models
    DecisionInput,
    DecisionFirewall,
    DecisionCharter,
    DecisionUmbra,
    DecisionOrchestrators,
    DecisionOutput,
    DecisionSummaryView,
    
    # Orchestrator views
    DAPView,
    PRFView,
    NTHView,
    COLView,
    
    # Type literals
    RiskProfile,
    RuleState,
    IdentityRisk,
    DAPRole,
    PRFPressure,
    OutputType,
    DecisionMode,
)

# ========= Conscience View Re-exports ======================================

from .data_models.conscience_view import ConscienceView

# ========= Models Re-exports ===============================================

from .data_models.models import (
    RiskLevel,
    SafetySignal,
    PolicyRisk,
)

# ========= Public API ======================================================

__all__ = [
    # Prompt envelope
    "PromptEnvelope",
    "PromptEnvelopeMeta",
    "PromptFlags",
    "PromptSource",
    "PromptTone",
    "PromptChannel",
    
    # Decision envelope
    "DecisionEnvelope",
    "DecisionInput",
    "DecisionFirewall",
    "DecisionCharter",
    "DecisionUmbra",
    "DecisionOrchestrators",
    "DecisionOutput",
    "DecisionSummaryView",
    
    # Orchestrator views
    "DAPView",
    "PRFView",
    "NTHView",
    "COLView",
    
    # Type literals
    "RiskProfile",
    "RuleState",
    "IdentityRisk",
    "DAPRole",
    "PRFPressure",
    "OutputType",
    "DecisionMode",
    
    # Conscience
    "ConscienceView",
    
    # Models
    "RiskLevel",
    "SafetySignal",
    "PolicyRisk",
]
