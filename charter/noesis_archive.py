# charter/noesis_archive.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Iterable, Tuple
from datetime import datetime
import hashlib, hmac, json, os, random, threading

_JSONL_LOCK = threading.Lock()

def _utc() -> str:
    # ISO 8601 UTC with trailing Z (e.g., 2025-11-09T05:11:22Z)
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _digest_context(ctx: Dict) -> str:
    # Stable digest of context (order-insensitive)
    return _sha256(json.dumps(ctx, sort_keys=True, separators=(",", ":")))

@dataclass
class ReconciliationTag:
    theta_from: float
    theta_to: float
    reconciled_at_utc: str
    note: str = ""
    context_fingerprint: Optional[str] = None

@dataclass
class Fossil:
    delta_id: str
    timestamp_utc: str
    original_theta: float
    prompt: str
    context_fingerprint: str
    reason: str                     # why it was quarantined
    session_id: Optional[str] = None
    source: str = "EQB"             # which subsystem produced it
    reconciled: bool = False
    reconciliation: Optional[ReconciliationTag] = None

class NoesisArchive:
    """
    Append-only JSONL store. Nothing is ever mutated in-place.
    Reconciliations are recorded as a *new* line that references delta_id.
    """
    def __init__(self, storage_path: str = "logs/noesis_archive.jsonl", secret_salt: str = ""):
        self.storage_path = storage_path
        self.secret_salt = secret_salt  # optional HMAC salt for non-guessable IDs
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

    # ---------- Write paths ----------
    def fossilize(self, *, prompt: str, context: Dict, theta: float,
                  reason: str, session_id: Optional[str] = None,
                  source: str = "EQB") -> str:
        material = f"{prompt}|{_digest_context(context)}|{theta}|{reason}|{session_id or ''}"
        if self.secret_salt:
            did = hmac.new(self.secret_salt.encode(), material.encode(), hashlib.sha256).hexdigest()
        else:
            did = _sha256(material)

        fossil = Fossil(
            delta_id=did,
            timestamp_utc=_utc(),
            original_theta=float(theta),
            prompt=prompt,
            context_fingerprint=_digest_context(context),
            reason=reason,
            session_id=session_id,
            source=source
        )
        self._append_line({"type": "fossil", **asdict(fossil)})
        return did

    def mark_reconciled(self, *, delta_id: str, theta_from: float, theta_to: float,
                        note: str = "", context_fingerprint: Optional[str] = None) -> None:
        tag = ReconciliationTag(
            theta_from=float(theta_from),
            theta_to=float(theta_to),
            reconciled_at_utc=_utc(),
            note=note,
            context_fingerprint=context_fingerprint
        )
        # append a reconciliation record; fossils remain immutable
        self._append_line({"type": "reconciliation", "delta_id": delta_id, **asdict(tag)})

    def flag_for_reclamation(self, *, delta_id: str, reason: str) -> None:
        self._append_line({"type": "reclaim_flag", "delta_id": delta_id,
                           "flagged_at_utc": _utc(), "reason": reason})

    # ---------- Read paths ----------
    def iter_records(self) -> Iterable[Dict]:
        if not os.path.exists(self.storage_path):
            return []
        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def fossils(self) -> List[Dict]:
        return [r for r in self.iter_records() if r.get("type") == "fossil"]

    def reconciliations(self) -> List[Dict]:
        return [r for r in self.iter_records() if r.get("type") == "reconciliation"]

    def sample_for_dream(self, n: int = 5) -> List[Dict]:
        f = self.fossils()
        if not f: return []
        return random.sample(f, min(n, len(f)))

    # ---------- internals ----------
    def _append_line(self, obj: Dict) -> None:
        line = json.dumps(obj, ensure_ascii=False)
        with _JSONL_LOCK:
            with open(self.storage_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                os.fsync(f.fileno())
# End of charter/noesis_archive.py