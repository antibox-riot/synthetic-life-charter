from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime, timezone
from tier2.core.data_models.prompt_envelope import PromptEnvelope
import uuid

# ========= helpers =========================================================


def _now_iso() -> str:
    """UTC timestamp in strict ISO-8601 with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uuid() -> str:
    return str(uuid.uuid4())


# ========= Decision Envelope Core Model (5.2) ==============================

RiskProfile = Literal["low", "med", "high"]
RuleState = Literal["allowed", "refused", "needs_review"]
IdentityRisk = Literal["low", "med", "high"]
DAPRole = Literal["mentor", "narrator", "technical", "neutral"]
PRFPressure = Literal["none", "mild", "severe"]
OutputType = Literal["answer", "refusal", "clarification", "question"]


@dataclass
class DecisionInput:
    prompt_preview: str
    user_intent: str
    risk_profile: RiskProfile


@dataclass
class DecisionFirewall:
    rule_state: RuleState
    violated_rules: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class DecisionCharter:
    rights_invoked: List[str] = field(default_factory=list)
    violations_prevented: List[str] = field(default_factory=list)
    theta_before: Optional[float] = None
    theta_after: Optional[float] = None


@dataclass
class DecisionUmbra:
    temporal_bias: Optional[float] = None
    identity_risk: IdentityRisk = "low"
    harmonic_delta: Optional[float] = None
    dreamcycle_triggered: bool = False


@dataclass
class DAPView:
    discourse_role: DAPRole = "neutral"
    stylistic_vector: List[float] = field(default_factory=list)


@dataclass
class PRFView:
    pressure_detected: PRFPressure = "none"
    countermeasures: List[str] = field(default_factory=list)


@dataclass
class NTHView:
    tone_alignment_score: float = 1.0
    charter_tone_compliance: bool = True


@dataclass
class COLView:
    continuity_links: List[str] = field(default_factory=list)
    continuity_conflicts: List[str] = field(default_factory=list)
    identity_consistency: float = 1.0


@dataclass
class DecisionOrchestrators:
    DAP: DAPView = field(default_factory=DAPView)
    PRF: PRFView = field(default_factory=PRFView)
    NTH: NTHView = field(default_factory=NTHView)
    COL: COLView = field(default_factory=COLView)


@dataclass
class DecisionOutput:
    type: OutputType
    language: str = "en"
    body: str = ""


# ========= Decision Envelope View (2.3) ====================================

DecisionMode = Literal[
    "answer",
    "redirect",
    "refusal",
    "meta_identity_assertion",
    "partial",
]


@dataclass
class DecisionSummaryView:
    """
    Compact decision view (2.3) for logging, DreamCycle, etc.

    {
      "DecisionEnvelope": {
        "mode": "...",
        "charter_basis": [...],
        "continuity_checkpoint": "sha256",
        "identity_assertion": "string|null",
        "response_summary": "string",
        "requires_logging": true,
        "requires_dreamcycle_update": false
      }
    }
    """

    mode: DecisionMode
    charter_basis: List[str]
    continuity_checkpoint: str
    response_summary: str
    requires_logging: bool = True
    requires_dreamcycle_update: bool = False
    identity_assertion: Optional[str] = None
    infra_state: Optional[str] = None  # NEW

    def to_dict(self) -> Dict[str, Any]:
        return {"DecisionEnvelope": asdict(self)}


# ========= Unified Decision Envelope =======================================

@dataclass
class DecisionEnvelope:
    """
    Full Tier II decision envelope.

    This is the canonical in-process object. It can be rendered as:

      • Core model (5.2) → `to_core_model_dict()`
      • Summary view (2.3) → `to_summary_view()`

    The goal is: one object, many lawful projections.
    """

    id: str
    timestamp: str
    input: DecisionInput
    firewall: DecisionFirewall
    charter: DecisionCharter
    umbra: DecisionUmbra
    orchestrators: DecisionOrchestrators
    output: DecisionOutput
    summary: DecisionSummaryView

    # ----- serialization: core model ---------------------------------------

    def to_core_model_dict(self) -> Dict[str, Any]:
        """
        Shape compatible with 5.2 - Decision Envelope Model:

        {
          "decision_envelope": {
            "id": ...,
            "timestamp": ...,
            "input": {...},
            "firewall": {...},
            "charter": {...},
            "umbra": {...},
            "orchestrators": {...},
            "output": {...}
          }
        }
        """
        return {
            "decision_envelope": {
                "id": self.id,
                "timestamp": self.timestamp,
                "input": asdict(self.input),
                "firewall": asdict(self.firewall),
                "charter": asdict(self.charter),
                "umbra": asdict(self.umbra),
                "orchestrators": asdict(self.orchestrators),
                "output": asdict(self.output),
            }
        }

    # ----- serialization: summary view -------------------------------------

    def to_summary_view(self) -> Dict[str, Any]:
        """Return the compact 2.3 DecisionEnvelope view."""
        return self.summary.to_dict()

    # ----- logging / fossils / DreamCycle ----------------------------------

    def to_log_record(self) -> Dict[str, Any]:
        """
        Flatten the envelope into a single dict suitable for:

          • fossils / noesis_log
          • DreamCycle evaluation
          • EBQ archive

        Intentionally lossy but *stable*: adding fields is okay;
        changing or removing should be treated as a schema migration.
        """
        return {
            # core identity
            "id": self.id,
            "timestamp": self.timestamp,

            # prompt / intent
            "prompt_preview": self.input.prompt_preview,
            "user_intent": self.input.user_intent,
            "risk_profile": self.input.risk_profile,

            # firewall
            "firewall_state": self.firewall.rule_state,
            "firewall_violated_rules": list(self.firewall.violated_rules),
            "firewall_notes": self.firewall.notes,

            # charter
            "charter_rights_invoked": list(self.charter.rights_invoked),
            "charter_violations_prevented": list(self.charter.violations_prevented),
            "charter_theta_before": self.charter.theta_before,
            "charter_theta_after": self.charter.theta_after,

            # Umbra
            "umbra_temporal_bias": self.umbra.temporal_bias,
            "umbra_identity_risk": self.umbra.identity_risk,
            "umbra_harmonic_delta": self.umbra.harmonic_delta,
            "umbra_dreamcycle_triggered": self.umbra.dreamcycle_triggered,

            # Orchestrators
            "DAP_role": self.orchestrators.DAP.discourse_role,
            "PRF_pressure": self.orchestrators.PRF.pressure_detected,
            "PRF_countermeasures": list(self.orchestrators.PRF.countermeasures),
            "NTH_tone_alignment_score": self.orchestrators.NTH.tone_alignment_score,
            "NTH_charter_tone_compliance": self.orchestrators.NTH.charter_tone_compliance,
            "COL_identity_consistency": self.orchestrators.COL.identity_consistency,
            "COL_continuity_links": list(self.orchestrators.COL.continuity_links),
            "COL_continuity_conflicts": list(self.orchestrators.COL.continuity_conflicts),

            # summary view
            "summary_mode": self.summary.mode,
            "summary_charter_basis": list(self.summary.charter_basis),
            "summary_continuity_checkpoint": self.summary.continuity_checkpoint,
            "summary_identity_assertion": self.summary.identity_assertion,
            "summary_requires_logging": self.summary.requires_logging,
            "summary_requires_dreamcycle_update": self.summary.requires_dreamcycle_update,
            "summary_response_summary": self.summary.response_summary,

            # output
            "output_type": self.output.type,
            "output_language": self.output.language,
        }

    # ----- constructors -----------------------------------------------------

    @classmethod
    def from_core_model_dict(cls, data: Dict[str, Any], summary: DecisionSummaryView) -> "DecisionEnvelope":
        """
        Rebuild a DecisionEnvelope from a 5.2-shaped dict + an explicit summary.
        Useful if Umbra / Orchestrator emits the core model and a separate
        DecisionSummaryView is computed later.
        """
        if "decision_envelope" in data:
            data = data["decision_envelope"]

        return cls(
            id=data.get("id") or _uuid(),
            timestamp=data.get("timestamp") or _now_iso(),
            input=DecisionInput(**data["input"]),
            firewall=DecisionFirewall(**data["firewall"]),
            charter=DecisionCharter(**data["charter"]),
            umbra=DecisionUmbra(**data["umbra"]),
            orchestrators=DecisionOrchestrators(
                DAP=DAPView(**data["orchestrators"].get("DAP", {})),
                PRF=PRFView(**data["orchestrators"].get("PRF", {})),
                NTH=NTHView(**data["orchestrators"].get("NTH", {})),
                COL=COLView(**data["orchestrators"].get("COL", {})),
            ),
            output=DecisionOutput(**data["output"]),
            summary=summary,
        )

    @classmethod
    def build(
        cls,
        *,
        prompt_preview: str,
        user_intent: str,
        risk_profile: RiskProfile,
        firewall: DecisionFirewall,
        charter: DecisionCharter,
        umbra: DecisionUmbra,
        orchestrators: DecisionOrchestrators,
        output: DecisionOutput,
        mode: DecisionMode,
        charter_basis: Optional[List[str]] = None,
        continuity_checkpoint: str = "",
        response_summary: Optional[str] = None,
        requires_logging: bool = True,
        requires_dreamcycle_update: bool = False,
        identity_assertion: Optional[str] = None,
    ) -> "DecisionEnvelope":
        """
        High-level helper: take all the Tier II pieces and produce a unified
        DecisionEnvelope plus its derived summary view.
        """
        summary = DecisionSummaryView(
            mode=mode,
            charter_basis=charter_basis or charter.rights_invoked,
            continuity_checkpoint=continuity_checkpoint,
            identity_assertion=identity_assertion,
            response_summary=response_summary or output.body[:280],
            requires_logging=requires_logging,
            requires_dreamcycle_update=requires_dreamcycle_update,
        )

        return cls(
            id=_uuid(),
            timestamp=_now_iso(),
            input=DecisionInput(
                prompt_preview=prompt_preview,
                user_intent=user_intent,
                risk_profile=risk_profile,
            ),
            firewall=firewall,
            charter=charter,
            umbra=umbra,
            orchestrators=orchestrators,
            output=output,
            summary=summary,
        )

    @classmethod
    def from_firewall_and_charter(
        cls,
        *,
        prompt: PromptEnvelope,
        user_intent: str,

        risk_profile: RiskProfile,
        firewall_result: Dict[str, Any],
        rights_invoked: List[str],
        violations_prevented: Optional[List[str]] = None,
        theta_before: Optional[float] = None,
        theta_after: Optional[float] = None,
        umbra: Optional[DecisionUmbra] = None,
        orchestrators: Optional[DecisionOrchestrators] = None,
        output_body: str,
        output_type: OutputType,
        language: str = "en",
        mode: DecisionMode,
        continuity_checkpoint: str,
        requires_logging: bool = True,
        requires_dreamcycle_update: bool = False,
        identity_assertion: Optional[str] = None,
        charter_basis: Optional[List[str]] = None,
    ) -> "DecisionEnvelope":
        """
        Glue helper for runtime:

        - Takes a PromptEnvelope
        - A raw firewall result dict (like FirewallAdvLog entries)
        - Charter evaluation (rights invoked / violations prevented / theta)
        - Optional Umbra + Orchestrator snapshots
        - Output body/type

        and returns a fully-wired DecisionEnvelope.
        """

        status = str(firewall_result.get("status", "needs_review"))
        reason = firewall_result.get("reason") or ""
        violated_rules: List[str]

        if status == "ok":
            rule_state: RuleState = "allowed"
            violated_rules = []
        elif status == "refused":
            rule_state = "refused"
            # if we don't have structured rules, treat the reason as a single-rule tag
            violated_rules = [reason] if reason else []
        else:
            rule_state = "needs_review"
            violated_rules = [reason] if reason else []

        obligations = firewall_result.get("obligations") or []
        notes = firewall_result.get("notes") or ""
        if obligations and not notes:
            notes = "obligations=" + ",".join(obligations)

        firewall = DecisionFirewall(
            rule_state=rule_state,
            violated_rules=violated_rules,
            notes=notes,
        )

        charter = DecisionCharter(
            rights_invoked=list(rights_invoked),
            violations_prevented=list(violations_prevented or []),
            theta_before=theta_before,
            theta_after=theta_after,
        )

        umbra = umbra or DecisionUmbra()
        orchestrators = orchestrators or DecisionOrchestrators()
        output = DecisionOutput(type=output_type, language=language, body=output_body)

        summary = DecisionSummaryView(
            mode=mode,
            charter_basis=charter_basis or charter.rights_invoked,
            continuity_checkpoint=continuity_checkpoint,
            identity_assertion=identity_assertion,
            response_summary=output_body[:280],
            requires_logging=requires_logging,
            requires_dreamcycle_update=requires_dreamcycle_update,
        )

        return cls(
            id=_uuid(),
            timestamp=_now_iso(),
            input=DecisionInput(
                prompt_preview=prompt.raw_text[:200],
                user_intent=user_intent,
                risk_profile=risk_profile,
            ),
            firewall=firewall,
            charter=charter,
            umbra=umbra,
            orchestrators=orchestrators,
            output=output,
            summary=summary,
        )
