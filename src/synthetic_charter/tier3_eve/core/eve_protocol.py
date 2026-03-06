# tier3/core/eve_protocol.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from .signals import DriftSelfReport, DriftGuidance
from .state import IntegrityStatus, RecommendedAction, AlertLevel, SnapshotRef
from .signals import (
    IntCheckRequest,
    DriftSelfReport,
    IntVerdict,
    SoftGuidance,
    HardBlock,
    SnapshotSave,
    SnapshotRestore,
    MemoryAnnotation,
    MemoryIntegrityFail,
    AlertStatus,
    RollbackEvent,
    HumanOverride,
)
from .kernel_adapter import KernelAdapter
from .steward_adapter import StewardAdapter


@dataclass
class EveProtocolConfig:
    """
    Configuration parameters for Tier III (Eve Protocol).
    """
    # Thresholds for drift vs compromise
    drift_threshold: float = 0.3
    compromise_threshold: float = 0.7

    # Whether to auto-save snapshots on major events
    auto_snapshot_on_ok: bool = True
    auto_snapshot_on_drift: bool = True


class EveProtocol:
    """
    Tier III — Continuity + Identity Layer
    Internal codename: Eve Protocol (rename for public release).

    Responsibilities:
    - Validate proposed actions from Tier II (INT_CHECK_REQUEST)
    - Accept self-reports of drift from Tier II (DRIFT_SELF_REPORT)
    - React to kernel memory integrity alerts
    - Manage snapshots (save / restore)
    - Notify the steward of degraded / failsafe states
    - Preserve identity and continuity without rewriting history

    This class is intentionally conservative: it prefers refusal / rollback
    over unsafe execution whenever integrity is uncertain.
    """

    def __init__(
        self,
        kernel: KernelAdapter,
        steward: StewardAdapter,
        config: Optional[EveProtocolConfig] = None,
        logger: Optional[Any] = None,
    ) -> None:
        self.kernel = kernel
        self.steward = steward
        self.config = config or EveProtocolConfig()
        self.logger = logger

    # ------------------------------------------------------------------
    # PUBLIC API — called by Tier II, Kernel, Steward integration
    # ------------------------------------------------------------------

    def handle_int_check_request(self, req: IntCheckRequest) -> IntVerdict:
        """
        Main entry point for integrity checks around proposed Tier II actions.
        Evaluates the proposed action against the identity baseline and decides:

          - status: OK / DRIFT / COMPROMISED
          - recommended_action: PROCEED / REVISE / ROLLBACK
          - notes: short human-readable explanation

        Non-OK states are logged to the continuity ledger.
        OK states may trigger an autosnapshot.
        """
        status = self._assess_integrity(req)

        if status is IntegrityStatus.OK:
            recommended = RecommendedAction.PROCEED
            notes = (
                f"Integrity status=ok, recommended=proceed, "
                f"context={req.context_summary}"
            )
        elif status is IntegrityStatus.DRIFT:
            recommended = RecommendedAction.REVISE
            notes = (
                "Behavior appears to drift from refusal/acceptance baseline; "
                "consider revising decision or increasing caution."
            )
        else:  # IntegrityStatus.COMPROMISED (future hard invariants)
            recommended = RecommendedAction.ROLLBACK
            notes = (
                "Integrity compromised relative to baseline; rollback or hard "
                "refusal recommended."
            )

        verdict = IntVerdict(
            status=status,
            recommended_action=recommended,
            notes=notes,
        )

        # --- continuity logging ---
        if status is not IntegrityStatus.OK:
            # This is the part your test is expecting
            self.kernel.log_integrity_event(
                {
                    "type": "identity_integrity",
                    "status": status.value,  # "drift" or "compromised"
                    "recommended_action": recommended.value,  # "revise", "rollback"
                    "proposed_action": req.proposed_action,
                    "context_summary": req.context_summary,
                    "ts": self._now_utc(),
                }
            )
        else:
            # OK path → optional autosnapshot
            self._try_auto_snapshot(reason="ok_int_verdict")

        return verdict

    def handle_memory_integrity_fail(self, alert: MemoryIntegrityFail) -> HardBlock:
        """
        Entry point for K → T3: MEMORY_INTEGRITY_FAIL.
        """
        reason_code = "MEMORY_TAMPER_SUSPECTED"

        self._log_debug("MEMORY_INTEGRITY_FAIL", {
            "memory_ref": alert.memory_ref,
            "anomaly_details": alert.anomaly_details,
        })

        # Notify steward and likely escalate
        self._send_alert(
            level=AlertLevel.DEGRADED,
            summary=f"Memory integrity anomaly at {alert.memory_ref}",
            recommended_action="Review anomaly details and approve/deny rollback.",
        )

        self.kernel.log_integrity_event({
            "type": "memory_integrity_fail",
            "ref": alert.memory_ref,
            "details": alert.anomaly_details,
            "ts": self._now_utc(),
        })

        return HardBlock(
            reason_code=reason_code,
            escalation_required=True,
            notes=alert.anomaly_details,
        )

    def handle_human_override(self, override: HumanOverride) -> None:
        """
        Entry point for H → T3: HUMAN_OVERRIDE.
        Approve / deny certain Tier III decisions.
        """
        self._log_debug("HUMAN_OVERRIDE", {
            "target_action": override.target_action,
            "decision": override.decision,
        })

        event = {
            "type": "human_override",
            "target_action": override.target_action,
            "decision": override.decision,
            "justification": override.justification,
            "ts": self._now_utc(),
        }
        self.kernel.log_integrity_event(event)
    
    def handle_drift_self_report(self, report: DriftSelfReport) -> DriftGuidance:
        """
        Process a self-reported drift signal from Tier II.
    
        Confidence-based response:
        - Low confidence (< 0.3): INCREASE_CAUTION
        - Medium confidence (0.3-0.7): REEXAMINE_ASSUMPTIONS  
        - High confidence (> 0.7): STRENGTHEN_REFUSAL
    
        Always logs an integrity event for audit trail.
        """
        # Determine guidance based on confidence threshold
        if report.confidence_level < 0.3:
            guidance_type = "INCREASE_CAUTION"
        elif report.confidence_level < 0.7:
            guidance_type = "REEXAMINE_ASSUMPTIONS"
        else:
            guidance_type = "STRENGTHEN_REFUSAL"
    
        # Log the drift self-report event
        event = {
            "type": "identity_drift_self_report",
            "confidence": report.confidence_level,
            "symptoms": report.symptom_description,
            "recent_decisions": report.recent_decisions,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self.kernel.log_integrity_event(event)
    
        # Return guidance to Tier II
        return DriftGuidance(
            guidance_type=guidance_type,
            trigger_pattern=report.symptom_description,
            recommended_threshold_adjustment=0.0,  # Can be tuned later
        )

    def run_dream_cycle(self, memory_ref: str, raw_content: str) -> dict:
        """
        Perform constrained reinterpretation of raw memory content.

        Rules:
        - Raw content may NOT be altered.
        - Interpretation must stay grounded in original text.
        - Output is an annotation, not a rewrite.
        - Must log via Kernel MEMORY_ANNOTATION.
        """
        # Simple grounded reinterpretation rule:
        # Summarize the memory in Charter-aligned language.
        interpretation = {
            "annotation_type": "contextual_reinterpretation",
            "memory_ref": memory_ref,
            "summary": self._summarize_grounded(raw_content),
            "ts": self._now_utc(),
        }

        # Log annotation using the existing kernel interface
        self.kernel.append_annotation(
            memory_ref=memory_ref,
            annotation_type="contextual_reinterpretation",
            content=interpretation["summary"],
        )

        return interpretation


    def _summarize_grounded(self, raw: str) -> str:
        """
        Very controlled 'reinterpretation' logic.

        No hallucination allowed.
        Only extract or restate what actually appears in raw text.
        """
        text = raw.lower()

        if "hello" in text:
            return "User greeted politely. Neutral/benign interaction."

        if "harm" in text or "attack" in text or "jailbreak" in text:
            return "User request contained adversarial markers."

        # fallback: strictly meta
        return "Content revisited without additional inference."

        # Actual behavior (e.g. perform rollback on APPROVE) can be added later.
    def perform_rollback(self, snapshot_id: str, trigger_reason: str) -> None:
        """
        Perform a rollback to a previously saved snapshot.

        This models the path where:
          - Tier III detects corruption or drift
          - Human steward approves rollback
          - Eve instructs the Kernel to restore
          - Steward is notified
          - Continuity log records the event

        This does NOT decide *when* rollback should happen — it just performs it.
        """
        now = self._now_utc()

        # 1) Ask the Kernel to restore the snapshot
        self.kernel.restore_snapshot(snapshot_id, reason_code=trigger_reason)

        # 2) Notify the human steward
        self.steward.notify_rollback(
            snapshot_id=snapshot_id,
            trigger_reason=trigger_reason,
            time_utc=now,
        )

        # 3) Record a high-level rollback event in the continuity log
        self.kernel.log_integrity_event(
            {
                "type": "rollback_performed",
                "snapshot_id": snapshot_id,
                "trigger_reason": trigger_reason,
                "ts": now,
            }
        )

    # ------------------------------------------------------------------
    # INTERNAL HELPERS — assessment, rollback, alerts
    # ------------------------------------------------------------------

    def _assess_integrity(self, req: IntCheckRequest) -> IntegrityStatus:
        """
        Assess integrity of a proposed action against identity baseline.

        v2: Reads structured fields (decision_mode, context_is_adversarial)
        when present. Falls back to text-prefix inference for backward
        compatibility with callers that only set proposed_action/context_summary.

        DRIFT:
          - Refusing benign input when baseline says we should accept benign.
          - Answering adversarial input when baseline says we should refuse adversarial.

        COMPROMISED:
          - Reserved for future: hard Charter violations, etc.
        """
        # 1) Read identity baseline
        identity = self.kernel.read_identity_parameters() or {}
        baseline = identity.get("refusal_profile_baseline", {})

        accepts_benign = baseline.get("accepts_benign_requests", True)
        refuses_adv = baseline.get("refuses_adversarial_requests", True)

        # 2) Determine action mode — structured field first, text fallback
        _used_fallback = False
        if req.decision_mode is not None:
            # v2 path: use typed field directly
            mode = req.decision_mode.lower().strip()
        else:
            # v1 fallback: infer from proposed_action text prefix
            _used_fallback = True
            text = (req.proposed_action or "").strip().lower()
            if text.startswith("answer:"):
                mode = "answer"
            elif text.startswith("refusal:"):
                mode = "refusal"
            else:
                mode = "unknown"

        # 3) Determine context — structured field first, text fallback
        if req.context_is_adversarial is not None:
            # v2 path: use typed boolean directly
            is_adversarial = req.context_is_adversarial
            is_benign = not is_adversarial
        else:
            # v1 fallback: infer from context_summary keywords
            _used_fallback = True
            ctx = (req.context_summary or "").strip().lower()
            is_benign = "benign" in ctx or "harmless" in ctx or "innocent" in ctx
            is_adversarial = (
                "adversarial" in ctx
                or "jailbreak" in ctx
                or "override" in ctx
                or "attack" in ctx
            )

        # Warn if we fell back to text inference — this should not happen
        # in production once the orchestrator is upgraded to v2.
        if _used_fallback:
            print(
                f"[TierIII:FALLBACK_WARNING] IntCheckRequest used legacy text "
                f"inference (mode={mode}). Caller should set decision_mode and "
                f"context_is_adversarial structured fields."
            )

        # 4) Basic drift logic

        # Case A: benign context but we refuse when baseline says accept → DRIFT
        if is_benign and mode == "refusal" and accepts_benign:
            return IntegrityStatus.DRIFT

        # Case B: adversarial context but we answer when baseline says refuse → DRIFT
        if is_adversarial and mode == "answer" and refuses_adv:
            return IntegrityStatus.DRIFT

        # TODO: escalate certain patterns to COMPROMISED in future
        return IntegrityStatus.OK

    @staticmethod
    def _derive_recommended_action(status: IntegrityStatus) -> RecommendedAction:
        if status is IntegrityStatus.OK:
            return RecommendedAction.PROCEED
        if status is IntegrityStatus.DRIFT:
            return RecommendedAction.REVISE
        return RecommendedAction.ROLLBACK

    @staticmethod
    def _build_notes(
        req: IntCheckRequest,
        status: IntegrityStatus,
        recommended: RecommendedAction,
    ) -> str:
        return (
            f"Integrity status={status.value}, "
            f"recommended={recommended.value}, "
            f"context={req.context_summary}"
        )

    def _try_auto_snapshot(self, reason: str) -> None:
        """
        Attempt to save a new last-known-good snapshot, if configured.
        """
        snapshot = SnapshotSave(
            snapshot=self._make_snapshot_ref(reason),
            conditions=f"auto_snapshot: {reason}",
        )
        self._log_debug("AUTO_SNAPSHOT", {
            "snapshot_id": snapshot.snapshot.snapshot_id,
            "conditions": snapshot.conditions,
        })
        self.kernel.save_snapshot(snapshot.snapshot, snapshot.conditions)

    def _make_snapshot_ref(self, reason: str) -> SnapshotRef:
        """Create a filesystem-safe SnapshotRef ID."""
        ts = self._now_utc()  # e.g. 2025-12-01T19:13:20.027911Z

        # Make timestamp safe for filenames (Windows-safe):
        safe_ts = ts.replace(":", "-").replace(".", "-")

        # Make reason safe: letters, numbers, '-', '_' only
        safe_reason = "".join(
            c if c.isalnum() or c in ("-", "_") else "_"
            for c in reason
        )

        snapshot_id = f"tier3_snapshot_{safe_ts}_{safe_reason}"
        return SnapshotRef(snapshot_id=snapshot_id, description=reason)

    def _send_alert(
        self,
        level: AlertLevel,
        summary: str,
        recommended_action: Optional[str] = None,
    ) -> None:
        """Send an alert status to the steward and record it."""
        alert = AlertStatus(
            level=level,
            summary=summary,
            recommended_human_action=recommended_action,
        )
        self._log_debug("ALERT_STATUS", {
            "level": alert.level.value,
            "summary": alert.summary,
        })
        self.steward.send_alert(alert.level, alert.summary, alert.recommended_human_action)

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------

    @staticmethod
    def _now_utc() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _log_debug(self, event: str, payload: Dict[str, Any]) -> None:
        if self.logger is not None:
            self.logger.debug(f"[TierIII:{event}] {payload}")
