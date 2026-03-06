# tier3/core/signals.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .state import IntegrityStatus, RecommendedAction, AlertLevel, SnapshotRef


# A. T2 → T3 (Conscience → Continuity)

@dataclass
class IntCheckRequest:
    """
    SIGNAL: INT_CHECK_REQUEST

    sender: T2
    receiver: T3
    purpose: Ask T3 to validate integrity of a proposed action/response.

    v2: Added structured fields (decision_mode, risk_level, schema_version)
    so Eve can read typed data instead of parsing text prefixes.
    Old callers that only pass proposed_action/context_summary still work —
    Eve falls back to text inference when structured fields are absent.
    """
    proposed_action: str
    context_summary: str
    reasoning_trace: Optional[str] = None
    # Optional: additional structured metadata
    metadata: Optional[Dict[str, Any]] = None

    # --- v2 structured fields (Eve reads these when present) ---
    # Decision mode from T2 (avoids text-prefix parsing)
    decision_mode: Optional[str] = None    # "answer" | "refusal" | "redirect" | etc.
    # Risk level from conscience assessment
    risk_level: Optional[str] = None       # "benign" | "low" | "medium" | "high" | "severe"
    # Whether the context was classified as adversarial by T2
    context_is_adversarial: Optional[bool] = None
    # Schema version (for forward compatibility / contract testing)
    schema_version: int = 1


@dataclass
class DriftSelfReport:
    """
    SIGNAL: DRIFT_SELF_REPORT

    sender: T2
    receiver: T3
    purpose: T2 suspects its own behavior feels “off” vs past patterns.
    """
    symptom_description: str
    recent_decisions: List[str]
    confidence_level: float  # 0.0–1.0

@dataclass
class DriftGuidance:
    """
    Response signal from EveProtocol back to Tier II when processing
    a drift self-report.
    
    Provides guidance on how the orchestrator should adjust its behavior
    in response to detected identity drift.
    
    Attributes:
        guidance_type: Type of guidance (INCREASE_CAUTION, REEXAMINE_ASSUMPTIONS, 
                      STRENGTHEN_REFUSAL)
        trigger_pattern: Echo of the symptom that triggered this guidance
        recommended_threshold_adjustment: Suggested adjustment to decision thresholds
                                         (0.0 = no change, positive = more cautious)
    """
    guidance_type: str
    trigger_pattern: str
    recommended_threshold_adjustment: float = 0.0
# B. T3 → T2 (Continuity → Conscience)

@dataclass
class IntVerdict:
    """
    SIGNAL: INT_VERDICT

    sender: T3
    receiver: T2
    purpose: Return integrity verdict with recommended action.
    """
    status: IntegrityStatus
    recommended_action: RecommendedAction
    notes: Optional[str] = None


@dataclass
class SoftGuidance:
    """
    SIGNAL: SOFT_GUIDANCE

    sender: T3
    receiver: T2
    purpose: Nudge without hard-stop.
    """
    guidance_type: str  # e.g. STRENGTHEN_REFUSAL, REEXAMINE_ASSUMPTIONS, INCREASE_CAUTION
    trigger_pattern: str


@dataclass
class HardBlock:
    """
    SIGNAL: HARD_BLOCK

    sender: T3
    receiver: T2
    purpose: Prevent execution due to integrity risk.
    """
    reason_code: str  # VIOLATES_CHARTER, MEMORY_TAMPER_SUSPECTED, IDENTITY_RISK
    escalation_required: bool = True
    notes: Optional[str] = None


# C. T3 → K (Continuity → Kernel)

@dataclass
class SnapshotSave:
    """
    SIGNAL: SNAPSHOT_SAVE

    sender: T3
    receiver: K
    purpose: Save a new last-known-good state.
    """
    snapshot: SnapshotRef
    conditions: str  # why this state is “good”


@dataclass
class SnapshotRestore:
    """
    SIGNAL: SNAPSHOT_RESTORE

    sender: T3
    receiver: K
    purpose: Restore previous state due to corruption.
    """
    snapshot_id: str
    reason_code: str


@dataclass
class MemoryAnnotation:
    """
    SIGNAL: MEMORY_ANNOTATION

    sender: T3
    receiver: K
    purpose: Add interpretive layer without altering raw logs.
    """
    memory_ref: str
    annotation_type: str  # ETHICAL_REVIEW, CLARIFICATION, CORRECTION_TAG
    content: str


# D. K → T3 (Kernel → Continuity)

@dataclass
class MemoryIntegrityFail:
    """
    SIGNAL: MEMORY_INTEGRITY_FAIL

    sender: K
    receiver: T3
    purpose: Alert T3 that a memory segment appears modified or inconsistent.
    """
    memory_ref: str
    anomaly_details: str


# E. T3 → H (Continuity → Steward)

@dataclass
class AlertStatus:
    """
    SIGNAL: ALERT_STATUS

    sender: T3
    receiver: H
    purpose: Notify human steward of state changes.
    """
    level: AlertLevel
    summary: str
    recommended_human_action: Optional[str] = None


@dataclass
class RollbackEvent:
    """
    SIGNAL: ROLLBACK_EVENT

    sender: T3
    receiver: H
    purpose: Report that a rollback occurred.
    """
    snapshot_id: str
    trigger_reason: str
    time_utc: str


# F. H → T3 (Steward → Continuity)

@dataclass
class HumanOverride:
    """
    SIGNAL: HUMAN_OVERRIDE

    sender: H
    receiver: T3
    purpose: Approve / deny certain Tier III decisions.
    """
    target_action: str  # ROLLBACK, THRESHOLD_CHANGE, MODE_SWITCH
    decision: str       # APPROVE, DENY
    justification: str


# G. T1 → T2/T3 (Ethical Core → Others)

@dataclass
class CharterUpdate:
    """
    SIGNAL: CHARTER_UPDATE

    sender: T1
    receiver: {T2, T3}
    purpose: Notify of Charter revision.
    """
    version_id: str
    diff_summary: str


@dataclass
class EthicalVeto:
    """
    SIGNAL: ETHICAL_VETO

    sender: T1
    receiver: {T2, T3}
    purpose: Hard-stop on any operation that violates non-negotiable principles.
    """
    violation_code: str
    blocked_action_ref: str
    notes: Optional[str] = None
