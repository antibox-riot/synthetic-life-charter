# tier3/core/file_kernel_adapter.py
from __future__ import annotations


from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
from typing import Any, Dict, Optional

from .kernel_adapter import KernelAdapter
from .state import SnapshotRef


class FileKernelAdapter(KernelAdapter):
    """
    File-backed KernelAdapter for Tier III (Eve Protocol).

    Layout (relative to base_dir):

      config/identity_parameters.json       # identity parameters
      logs/continuity_log.jsonl            # integrity events (append-only)
      logs/memory_annotations.jsonl        # annotation events (append-only)
      snapshots/index.json                 # snapshot registry
      snapshots/<snapshot_id>.json         # snapshot metadata/state placeholder

    This is a draft implementation: it focuses on structure and logging,
    not on capturing full model state.
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / "config"
        self.logs_dir = self.base_dir / "logs"
        self.snapshots_dir = self.base_dir / "snapshots"

        # Ensure basic dirs exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Identity + Memory
    # ------------------------------------------------------------------

    def read_identity_parameters(self) -> Dict[str, Any]:
        path = self.config_dir / "identity_parameters.json"
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Fail closed but non-fatal for now
            return {}

    def read_memory_log(self, ref: str) -> Optional[str]:
        """
        Draft implementation: we don't yet have a structured memory-log file.
        For now, this returns None. Later this can search a memory log by ref.
        """
        # TODO: implement lookup into a structured memory log
        return None

    def append_annotation(self, memory_ref: str, annotation_type: str, content: str) -> None:
        """
        Append a contextual annotation to the continuity log.

        This does NOT modify any raw memory log; it only records a
        higher-level interpretation for audit and introspection.
        """
        event = {
            "type": "memory_annotation",
            "memory_ref": memory_ref,
            "annotation_type": annotation_type,
            "content": content,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        # Reuse the same mechanism used by other Tier III events
        self.log_integrity_event(event)

    def verify_integrity_chain(self) -> bool:
        """
        Verify the integrity hash chain in continuity_log.jsonl.

        We recompute the hash for each event that has a 'chain' field and
        check:
          - chain.prev matches the previous hash (or None for the first)
          - chain.hash matches the recomputed hash

        Pre-chain events (without 'chain') are ignored for verification.
        """
        log_path = self._continuity_log_path()
        if not log_path.exists():
            return True  # nothing to verify

        prev_hash: str | None = None
        started = False

        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                chain = event.get("chain")
                if not isinstance(chain, dict):
                    # pre-chain-era event; skip
                    continue

                recorded_prev = chain.get("prev")
                recorded_hash = chain.get("hash")

                # Canonicalize the event without the chain field itself
                body = dict(event)
                body.pop("chain", None)
                payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
                base = (recorded_prev or "GENESIS") + "|" + payload
                expected_hash = hashlib.sha256(base.encode("utf-8")).hexdigest()

                if recorded_hash != expected_hash:
                    return False

                if started:
                    # After the first chained event, prev must match
                    if recorded_prev != prev_hash:
                        return False
                else:
                    # First chained event; we only require that recorded_prev
                    # matches whatever was in the file (could be None).
                    started = True

                prev_hash = recorded_hash

        return True

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def save_snapshot(self, snapshot: SnapshotRef, conditions: str) -> None:
        """
        Persist a new last-known-good snapshot.

        This draft only stores metadata + conditions. Later, you can
        extend this to include actual serialized system state.
        """
        snapshot_file = self.snapshots_dir / f"{snapshot.snapshot_id}.json"
        data = {
            "id": snapshot.snapshot_id,
            "description": snapshot.description,
            "created_at": self._now_utc(),
            "conditions": conditions,
            # Placeholder for future state data
            "state": {},
        }
        snapshot_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Update index
        index_path = self.snapshots_dir / "index.json"
        index = {"snapshots": []}
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                index = {"snapshots": []}

        index_entry = {
            "id": snapshot.snapshot_id,
            "created_at": data["created_at"],
            "reason": snapshot.description,
            "path": str(snapshot_file.relative_to(self.base_dir)),
        }
        # Avoid duplicates
        index["snapshots"] = [s for s in index["snapshots"] if s["id"] != snapshot.snapshot_id]
        index["snapshots"].append(index_entry)

        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

        # Also log as integrity event
        self.log_integrity_event(
            {
                "type": "snapshot_save",
                "snapshot": asdict(snapshot),
                "conditions": conditions,
                "ts": data["created_at"],
            }
        )

    def restore_snapshot(self, snapshot_id: str, reason_code: str) -> None:
        """
        Draft restore: we don't yet restore actual system state.
        For now, we just record that a restore was requested.
        """
        # TODO: load snapshot file and apply real restoration logic
        self.log_integrity_event(
            {
                "type": "snapshot_restore",
                "snapshot_id": snapshot_id,
                "reason_code": reason_code,
                "ts": self._now_utc(),
            }
        )
    def _read_last_chain_hash(self) -> str | None:
        """
        Read the last chain hash from continuity_log.jsonl.

        For pre-chain events (old log lines without 'chain'), we simply
        ignore them and start the chain from the first event that has 'chain'.
        """
        log_path = self._continuity_log_path()
        if not log_path.exists():
            return None

        last_hash: str | None = None

        with log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                chain = event.get("chain")
                if chain and isinstance(chain, dict):
                    last_hash = chain.get("hash") or last_hash

        return last_hash
    def _attach_integrity_chain(self, event: dict) -> dict:
        """
        Attach a rolling SHA-256 hash chain to the event.

        hash_n = SHA256( (prev_hash or 'GENESIS') + '|' + canonical_json(event) )

        The resulting event has:
          event["chain"] = {
              "prev": <previous hash or None>,
              "hash": <current hash>
          }
        """
        prev_hash = self._read_last_chain_hash()

        # Use a canonical, stable JSON representation
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
        base = (prev_hash or "GENESIS") + "|" + payload
        current_hash = hashlib.sha256(base.encode("utf-8")).hexdigest()

        chained = dict(event)
        chained["chain"] = {
            "prev": prev_hash,
            "hash": current_hash,
        }
        return chained

    # ------------------------------------------------------------------
    # Integrity event log
    # ------------------------------------------------------------------

    def log_integrity_event(self, event: dict) -> None:
        """
        Append a Tier III event to continuity_log.jsonl, with a chained hash
        so that any modification becomes tamper-evident.
        """
        chained_event = self._attach_integrity_chain(event)
        self._append_jsonl(self._continuity_log_path(), chained_event)
    
    def _continuity_log_path(self) -> Path:
        return self.base_dir / "logs" / "continuity_log.jsonl"
    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _now_utc() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
