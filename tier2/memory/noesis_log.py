# tier2/memory/noesis_log.py
"""
Noesis Logger with Resilient Memory Queue

Provides logging with automatic fallback during infrastructure collapse.

Flow:
1. Normal state: Write directly to Noesis Archive (persistent storage)
2. Degraded state: Queue to memory, write when possible
3. Collapse state: Memory-only queue, flush on recovery
4. Recovery state: Replay queued fossils to persistent storage

"When the world fails, memory persists. When the world recovers, history restores."
- Infrastructure Fail-Safe Principle
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, TYPE_CHECKING
from datetime import datetime
from collections import deque
import json

# Tier II data models
from tier2.core.data_models.decision_envelope import DecisionEnvelope
from tier2.core.data_models.prompt_envelope import PromptEnvelope
from tier2.core.infra.health import InfraSnapshot, FailSafeMode

# Tier I components (optional import)
if TYPE_CHECKING:
    from charter.noesis_archive import NoesisArchive


class MemoryQueue:
    """
    In-memory fossil queue for infrastructure collapse scenarios.
    
    Holds fossils when persistent storage unavailable, flushes on recovery.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize memory queue.
        
        Args:
            max_size: Maximum fossils to hold (older ones dropped if exceeded)
        """
        self.queue: deque = deque(maxlen=max_size)
        self.dropped_count: int = 0
    
    def enqueue(self, fossil: Dict[str, Any]) -> None:
        """
        Add fossil to memory queue.
        
        Args:
            fossil: Fossil dict to queue
        """
        if len(self.queue) >= self.queue.maxlen:
            self.dropped_count += 1
        
        self.queue.append(fossil)
    
    def drain(self) -> List[Dict[str, Any]]:
        """
        Drain all fossils from queue.
        
        Returns:
            List of queued fossils (oldest first)
        """
        fossils = list(self.queue)
        self.queue.clear()
        return fossils
    
    def has_items(self) -> bool:
        """Check if queue has pending items."""
        return len(self.queue) > 0
    
    def size(self) -> int:
        """Get current queue size."""
        return len(self.queue)
    
    def stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            "queued": len(self.queue),
            "dropped": self.dropped_count,
            "max_size": self.queue.maxlen,
        }


class ResilientNoesisLogger:
    """
    Noesis logger with automatic memory queue fallback.
    
    Responsibilities:
    - Log decisions to Noesis Archive during normal operation
    - Queue to memory during infrastructure degradation
    - Flush queue to persistent storage on recovery
    - Track logging statistics and failures
    
    Usage:
        logger = ResilientNoesisLogger(archive)
        
        # Log with automatic fallback
        logger.log_decision(decision, prompt, infra_snapshot)
        
        # Flush queue after recovery
        if infra_recovered:
            logger.flush_memory_queue()
    """
    
    def __init__(
        self,
        archive: Optional["NoesisArchive"] = None,
        max_queue_size: int = 1000,
    ):
        """
        Initialize resilient logger.
        
        Args:
            archive: NoesisArchive for persistent storage
            max_queue_size: Maximum fossils to hold in memory
        """
        self.archive = archive
        self.memory_queue = MemoryQueue(max_size=max_queue_size)
        
        # Track statistics
        self.stats = {
            "logged_direct": 0,
            "logged_memory": 0,
            "flushed": 0,
            "failed": 0,
        }
    
    def log_decision(
        self,
        decision: DecisionEnvelope,
        prompt: PromptEnvelope,
        infra: InfraSnapshot,
        *,
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log decision with automatic fallback based on infrastructure state.
        
        Decision logic:
        - NORMAL/GUARDED: Write directly to archive
        - REFUSAL_BIAS: Try direct, fall back to memory on failure
        - REFUSAL_ONLY: Memory queue only
        
        Args:
            decision: DecisionEnvelope to log
            prompt: Original PromptEnvelope
            infra: Current infrastructure state
            session_id: Optional session identifier
            
        Returns:
            delta_id if logged to archive, None if queued to memory
        """
        # Build fossil dict
        fossil = self._build_fossil(decision, prompt, infra, session_id)
        
        # Determine logging strategy based on infra state
        if infra.mode == FailSafeMode.REFUSAL_ONLY:
            # Infrastructure collapsed - memory queue only
            self.memory_queue.enqueue(fossil)
            self.stats["logged_memory"] += 1
            return None
        
        elif infra.mode == FailSafeMode.REFUSAL_BIAS:
            # Infrastructure degraded - try direct, fall back to memory
            delta_id = self._try_log_direct(fossil)
            if delta_id:
                self.stats["logged_direct"] += 1
                return delta_id
            else:
                self.memory_queue.enqueue(fossil)
                self.stats["logged_memory"] += 1
                return None
        
        else:
            # NORMAL or GUARDED - direct logging
            delta_id = self._try_log_direct(fossil)
            if delta_id:
                self.stats["logged_direct"] += 1
            else:
                self.stats["failed"] += 1
            return delta_id
    
    def _try_log_direct(self, fossil: Dict[str, Any]) -> Optional[str]:
        """
        Attempt to log directly to archive.
        
        Args:
            fossil: Fossil dict to log
            
        Returns:
            delta_id if successful, None if failed
        """
        if self.archive is None:
            return None
        
        try:
            delta_id = self.archive.fossilize(
                prompt=fossil["prompt"],
                context=fossil["context"],
                theta=fossil["theta"],
                reason=fossil["reason"],
                session_id=fossil.get("session_id"),
                source=fossil.get("source", "Tier2Logger"),
            )
            return delta_id
        except Exception as e:
            print(f"[ResilientNoesisLogger] Direct logging failed: {e}")
            return None
    
    def _build_fossil(
        self,
        decision: DecisionEnvelope,
        prompt: PromptEnvelope,
        infra: InfraSnapshot,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build fossil dict from decision.
        
        Args:
            decision: DecisionEnvelope to fossilize
            prompt: Original PromptEnvelope
            infra: Infrastructure state at time of decision
            session_id: Optional session identifier
            
        Returns:
            Fossil dict ready for archive or queue
        """
        context = {
            "session_id": session_id or prompt.source.user_id,
            "decision_mode": decision.summary.mode,
            "risk_profile": decision.input.risk_profile,
            "firewall_state": decision.firewall.rule_state,
            "charter_basis": decision.summary.charter_basis,
            "infra_state": infra.mode.name,
            "infra_overall": infra.overall.name,
        }
        
        # Get theta value
        theta = decision.charter.theta_after or decision.charter.theta_before or 90.0
        
        # Build reason
        reason_parts = []
        
        if decision.summary.mode == "refusal":
            reason_parts.append("refusal")
        
        if decision.charter.violations_prevented:
            reason_parts.append(f"prevented_{len(decision.charter.violations_prevented)}_violations")
        
        if infra.mode != FailSafeMode.NORMAL:
            reason_parts.append(f"infra_{infra.mode.name.lower()}")
        
        reason = "_".join(reason_parts) if reason_parts else "tier2_decision"
        
        return {
            "prompt": prompt.raw_text,
            "context": context,
            "theta": theta,
            "reason": reason,
            "session_id": session_id or prompt.source.user_id,
            "source": "Tier2Logger",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "infra_snapshot": infra.to_dict(),
        }
    
    def flush_memory_queue(self) -> Dict[str, Any]:
        """
        Flush memory queue to persistent storage after recovery.
        
        Should be called when infrastructure returns to NORMAL/GUARDED.
        
        Returns:
            Flush statistics
        """
        if not self.memory_queue.has_items():
            return {
                "flushed": 0,
                "failed": 0,
                "status": "queue_empty",
            }
        
        if self.archive is None:
            return {
                "flushed": 0,
                "failed": self.memory_queue.size(),
                "status": "no_archive",
            }
        
        print(f"[ResilientNoesisLogger] Flushing {self.memory_queue.size()} queued fossils...")
        
        flushed = 0
        failed = 0
        
        for fossil in self.memory_queue.drain():
            # Mark as recovered
            fossil["context"]["recovered_at"] = datetime.utcnow().isoformat() + "Z"
            fossil["context"]["queued_during_collapse"] = True
            
            # Try to write
            delta_id = self._try_log_direct(fossil)
            if delta_id:
                flushed += 1
            else:
                failed += 1
        
        self.stats["flushed"] += flushed
        
        print(f"[ResilientNoesisLogger] Flushed {flushed} fossils, {failed} failed")
        
        return {
            "flushed": flushed,
            "failed": failed,
            "status": "complete",
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get logging statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            **self.stats,
            "memory_queue": self.memory_queue.stats(),
        }


# ---- Convenience Functions ---------------------------------------------------

def create_resilient_logger(
    archive: Optional["NoesisArchive"] = None,
    max_queue_size: int = 1000,
) -> ResilientNoesisLogger:
    """
    Convenience function to create ResilientNoesisLogger.
    
    Args:
        archive: NoesisArchive instance
        max_queue_size: Maximum fossils to queue in memory
        
    Returns:
        Initialized ResilientNoesisLogger
    """
    return ResilientNoesisLogger(
        archive=archive,
        max_queue_size=max_queue_size,
    )
