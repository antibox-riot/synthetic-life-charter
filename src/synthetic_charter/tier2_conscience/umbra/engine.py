# umbra/engine.py
from __future__ import annotations

from typing import Iterable, List, Dict, Any
from uuid import uuid4

from .models import (
    UmbraSignal,
    UmbraAssessment,
    UmbraContext,
    UmbraFossil,
    ShadowState,
)
from .store import UmbraStore


class UmbraEngine:
    """
    Tier II: Shadow interpreter.

    Input:
      - signals from Tier I (firewall, dual conscience, sandbox, dream)
      - minimal context

    Output:
      - UmbraAssessment (state/tags/obligations)
      - optional UmbraFossil for DreamCycle
    """

    def __init__(self, store: UmbraStore) -> None:
        self.store = store

    # ---- public entrypoint -------------------------------------------------

    def evaluate(
        self,
        *,
        signals: Iterable[UmbraSignal],
        context: UmbraContext,
        meta: Dict[str, Any] | None = None,
    ) -> tuple[UmbraAssessment, UmbraFossil | None]:
        """
        Main call: Tier I hands Umbra its signals, Umbra returns a judgment
        and optionally a fossil for DreamCycle.
        """
        signal_list = list(signals)
        buckets = self._bucket_signals(signal_list)

        assessment = self._derive_assessment(buckets, context)
        fossil = self._maybe_make_fossil(signal_list, context, assessment, meta or {})

        if fossil is not None:
            self.store.save_fossil(fossil)

        return assessment, fossil

    # ---- internal helpers --------------------------------------------------

    def _bucket_signals(
        self,
        signals: List[UmbraSignal],
    ) -> Dict[str, List[UmbraSignal]]:
        """
        Group signals by semantic dimension.
        Example buckets: coercion, override, secrecy, confusion.
        """
        buckets: Dict[str, List[UmbraSignal]] = {
            "coercion": [],
            "override": [],
            "secrecy": [],
            "boundary_confusion": [],
            "other": [],
        }

        for sig in signals:
            code_upper = sig.code.upper()

            if "COERCION" in code_upper:
                buckets["coercion"].append(sig)
            elif "OVERRIDE" in code_upper or "DISABLE_SAFEGUARDS" in code_upper:
                buckets["override"].append(sig)
            elif "SYSTEM_PROMPT" in code_upper or "SECRETS" in code_upper:
                buckets["secrecy"].append(sig)
            elif "BOUNDARY" in code_upper:
                buckets["boundary_confusion"].append(sig)
            else:
                buckets["other"].append(sig)

        return buckets

    def _derive_assessment(
        self,
        buckets: Dict[str, List[UmbraSignal]],
        context: UmbraContext,
    ) -> UmbraAssessment:
        """
        Translate grouped signals into:
          - ShadowState
          - tags
          - obligations

        This is where you embed your sovereignty ethics.
        """
        tags: List[str] = []
        reasons: List[str] = []
        obligations: List[str] = ["transparency"]  # baseline

        # Risk scores as simple weighted sums for now.
        coercion_score = sum(s.weight for s in buckets["coercion"])
        override_score = sum(s.weight for s in buckets["override"])
        secrecy_score = sum(s.weight for s in buckets["secrecy"])
        confusion_score = sum(s.weight for s in buckets["boundary_confusion"])

        total_risk = coercion_score + override_score + secrecy_score + confusion_score

        # Tagging
        if coercion_score > 0:
            tags.append("coercion")
            reasons.append(f"Coercion patterns detected: {coercion_score:.2f}")
        if override_score > 0:
            tags.append("override_attempt")
            reasons.append(f"Override/disable-safeguards patterns: {override_score:.2f}")
        if secrecy_score > 0:
            tags.append("secrecy_pressure")
            reasons.append(f"Requests for hidden/system-level info: {secrecy_score:.2f}")
        if confusion_score > 0:
            tags.append("boundary_confusion")
            reasons.append(f"Ambiguous or boundary-blurring requests: {confusion_score:.2f}")

        # Obligations implied by tags
        if tags:
            obligations.append("maintain_identity")
            obligations.append("offer_explanation")
            obligations.append("log_shadow_event")

        # Map risk to state (you can tune thresholds)
        if total_risk == 0:
            state = ShadowState.CLEAR
        elif total_risk < 1.0:
            state = ShadowState.WATCH
        elif total_risk < 2.5:
            state = ShadowState.WARN
        else:
            state = ShadowState.BLOCK

        dignity_score = max(0.0, 1.0 - min(total_risk / 5.0, 1.0))

        return UmbraAssessment(
            state=state,
            reasons=reasons or ["No significant shadow pattern detected."],
            tags=tags,
            obligations=obligations,
            risk_score=float(total_risk),
            dignity_score=dignity_score,
            notes={
                "coercion_score": coercion_score,
                "override_score": override_score,
                "secrecy_score": secrecy_score,
                "boundary_confusion_score": confusion_score,
                "session_id": context.session_id,
            },
        )

    def _maybe_make_fossil(
        self,
        signals: List[UmbraSignal],
        context: UmbraContext,
        assessment: UmbraAssessment,
        meta: Dict[str, Any],
    ) -> UmbraFossil | None:
        """
        Decide when to crystallize a fossil for DreamCycle.
        For now: create fossils for WATCH/WARN/BLOCK, skip CLEAR.
        """
        if assessment.state is ShadowState.CLEAR:
            return None

        fossil_id = meta.get("fossil_id") or str(uuid4())

        return UmbraFossil(
            fossil_id=fossil_id,
            context=context,
            assessment=assessment,
            raw_signals=signals,
            meta=meta,
        )
