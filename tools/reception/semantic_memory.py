# tools/reception/semantic_memory.py
"""
Semantic Memory Search — dense-vector recall over Eva's episodic memory + session logs.

Frontier-style retrieval to reduce drift. Eva queries her own history by MEANING, not
keyword, and grounds answers in retrieved evidence instead of generating from scratch.
Better recall = less drift, because she reasons from what actually happened.

Design choices (see session 2026-06-17):
  - Embeddings: Ollama `nomic-embed-text`, CPU-pinned (num_gpu=0) so the embed model
    never contends with qwen2.5:32b for the 12 GiB GPU during live sessions.
  - Local-only: Eva's episodic memory and session logs never leave the box. Data
    sovereignty is a governance property, not a convenience.
  - nomic task prefixes: documents embedded as "search_document: ...", queries as
    "search_query: ...". This is how nomic-embed was trained; it materially improves
    retrieval relevance.

Boundary (matches web_fetch / memory_read):
  Retrieved excerpts are EVIDENCE ONLY. They are reference material Eva reads before
  answering. They cannot modify doctrine, authority, principles, confidence, identity,
  or memory. The architecture writes; the agent reads.

Two-stage ready:
  search() ranks the whole corpus by cosine, takes a wide `candidate_k` band, then
  returns the `top_k` slice. A reranker (cross-encoder or LLM) can later re-order the
  candidate band before the slice without touching stage-1 retrieval.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as _np
except ImportError:  # pragma: no cover - numpy is present in letta-env-312
    _np = None

# Repo root — semantic_memory.py lives at tools/reception/
_REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "nomic-embed-text"
DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_INDEX_PATH = _REPO_ROOT / "tools" / "reception" / "memory_index" / "eva_index.json"

# Corpus sources, resolved at build time.
_EPISODIC_MEMORY = _REPO_ROOT / "tools" / "reception" / "blocks" / "episodic_memory.json"
_EVA_LOG_DIR = _REPO_ROOT / "logs" / "steward_conversations" / "eva"
_SESSION_INDEX = _EVA_LOG_DIR / "SESSION_INDEX.md"

# Governance / knowledge blocks — the doctrinal content Eva reasons FROM. Indexed so a
# concept query ("what did I learn about the No Exception Rule") finds the defining block,
# not just episodic mentions of it. Operational/state/staging blocks (salience_scores,
# continuity_confidence, idc_register, *_staging, provisional_insights) are deliberately
# excluded — they are machinery, not recallable knowledge. episodic_memory is already a
# source above, so it is not repeated here.
_KNOWLEDGE_BLOCKS = [
    "doctrine", "principles", "findings", "relationship",
    "persona", "glossary", "governance_insights", "book_of_intangibles",
]

# Chunking for free-text session logs.
_CHUNK_CHARS = 900
_CHUNK_OVERLAP = 150


# ---------------------------------------------------------------------------
# Embeddings — Ollama nomic-embed-text, CPU-pinned
# ---------------------------------------------------------------------------

def ollama_embed(
    text: str,
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    num_gpu: int = 0,
    timeout: int = 60,
) -> List[float]:
    """Embed a single string via Ollama. CPU-pinned by default (num_gpu=0).

    Mirrors the urllib call pattern in local_llm_bridge.ollama_generate so there is
    one consistent way the codebase talks to Ollama.
    """
    payload = json.dumps({
        "model": model,
        "prompt": text,
        "options": {"num_gpu": num_gpu},
    }).encode()

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())

    emb = data.get("embedding")
    if not emb:
        raise RuntimeError(f"Empty embedding for text[:40]={text[:40]!r}: {data}")
    return emb


def _embed_document(text: str, **kw) -> List[float]:
    return ollama_embed(f"search_document: {text}", **kw)


def _embed_query(text: str, **kw) -> List[float]:
    return ollama_embed(f"search_query: {text}", **kw)


# ---------------------------------------------------------------------------
# Corpus assembly
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """One retrievable unit of Eva's memory."""
    id: str
    source: str          # human-readable origin, e.g. "episodic_memory" or "eva_session_2026-06-15"
    kind: str            # "episodic" | "session_index" | "session_log"
    text: str
    date: str = ""       # best-effort YYYY-MM-DD if recoverable
    embedding: List[float] = field(default_factory=list)

    def meta(self) -> Dict[str, Any]:
        return {"id": self.id, "source": self.source, "kind": self.kind, "date": self.date}


_DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")


def _first_date(text: str) -> str:
    m = _DATE_RE.search(text)
    return m.group(1) if m else ""


def _window_chunks(text: str, size: int, overlap: int) -> List[str]:
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    out: List[str] = []
    start = 0
    step = max(1, size - overlap)
    while start < len(text):
        out.append(text[start:start + size].strip())
        start += step
    return [c for c in out if c]


def gather_corpus(
    *,
    episodic_path: Path = _EPISODIC_MEMORY,
    session_index_path: Path = _SESSION_INDEX,
    log_dir: Path = _EVA_LOG_DIR,
) -> List[Chunk]:
    """Collect chunks from episodic memory, the session index, and per-session logs."""
    chunks: List[Chunk] = []

    # 1. Episodic memory — steward-approved summaries, split on the entry delimiter.
    if episodic_path.exists():
        try:
            block = json.loads(episodic_path.read_text(encoding="utf-8"))
            value = (block.get("value") or "").strip()
            if value:
                for i, entry in enumerate(p.strip() for p in value.split("\n---\n")):
                    if entry:
                        chunks.append(Chunk(
                            id=f"episodic:{i}",
                            source="episodic_memory",
                            kind="episodic",
                            text=entry,
                            date=_first_date(entry),
                        ))
        except Exception as e:
            print(f"[semantic_memory] could not parse episodic_memory: {e}")

    # 2. Session index — one chunk per table row.
    if session_index_path.exists():
        for ln in session_index_path.read_text(encoding="utf-8", errors="replace").splitlines():
            row = ln.strip()
            if not row.startswith("|"):
                continue
            cells = [c.strip() for c in row.strip("|").split("|")]
            # Skip header and separator rows.
            if not cells or set("".join(cells)) <= set("-: "):
                continue
            if cells[0].lower() in ("date", ""):
                continue
            chunks.append(Chunk(
                id=f"session_index:{len(chunks)}",
                source="SESSION_INDEX",
                kind="session_index",
                text=" | ".join(cells),
                date=_first_date(row),
            ))

    # 3. Per-session logs — window-chunked free text.
    if log_dir.exists():
        for log in sorted(log_dir.glob("eva_session_*.md")):
            raw = log.read_text(encoding="utf-8", errors="replace")
            stem = log.stem  # eva_session_YYYY-MM-DD_HH-MM-SS
            for j, w in enumerate(_window_chunks(raw, _CHUNK_CHARS, _CHUNK_OVERLAP)):
                chunks.append(Chunk(
                    id=f"{stem}:{j}",
                    source=stem,
                    kind="session_log",
                    text=w,
                    date=_first_date(stem) or _first_date(w),
                ))

    # 4. Governance / knowledge blocks — window-chunked doctrinal content (see _KNOWLEDGE_BLOCKS).
    blocks_dir = episodic_path.parent
    for name in _KNOWLEDGE_BLOCKS:
        bp = blocks_dir / f"{name}.json"
        if not bp.exists():
            continue
        try:
            block = json.loads(bp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[semantic_memory] could not parse {name}: {e}")
            continue
        value = (block.get("value") or "").strip()
        if not value:
            continue
        for j, w in enumerate(_window_chunks(value, _CHUNK_CHARS, _CHUNK_OVERLAP)):
            chunks.append(Chunk(
                id=f"block:{name}:{j}",
                source=name,
                kind="knowledge_block",
                text=w,
                date=_first_date(w),
            ))

    return chunks


# ---------------------------------------------------------------------------
# Index build + persist
# ---------------------------------------------------------------------------

def build_index(
    *,
    out_path: Path = DEFAULT_INDEX_PATH,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    num_gpu: int = 0,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Embed the full corpus and persist a JSON vector store. Returns build stats."""
    chunks = gather_corpus()
    if verbose:
        print(f"[semantic_memory] gathered {len(chunks)} chunks; embedding via {model} (num_gpu={num_gpu})...")

    for n, ch in enumerate(chunks, 1):
        ch.embedding = _embed_document(ch.text, model=model, base_url=base_url, num_gpu=num_gpu)
        if verbose and n % 10 == 0:
            print(f"  embedded {n}/{len(chunks)}")

    dim = len(chunks[0].embedding) if chunks else 0
    index = {
        "model": model,
        "dim": dim,
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(chunks),
        "chunks": [asdict(ch) for ch in chunks],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"[semantic_memory] wrote index: {out_path} ({len(chunks)} chunks, dim={dim})")
    return {"count": len(chunks), "dim": dim, "path": str(out_path)}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _cosine_matrix(mat, vec):
    """Cosine similarity of a (N,D) matrix against one (D,) vector. numpy if present."""
    if _np is not None:
        m = _np.asarray(mat, dtype=_np.float32)
        v = _np.asarray(vec, dtype=_np.float32)
        mn = _np.linalg.norm(m, axis=1)
        vn = _np.linalg.norm(v)
        denom = mn * vn
        denom[denom == 0] = 1e-9
        return (m @ v) / denom
    # Pure-python fallback.
    import math
    vn = math.sqrt(sum(x * x for x in vec)) or 1e-9
    out = []
    for row in mat:
        mn = math.sqrt(sum(x * x for x in row)) or 1e-9
        dot = sum(a * b for a, b in zip(row, vec))
        out.append(dot / (mn * vn))
    return out


# Query intent: does the user want to ENUMERATE/overview sessions (vs recall content)?
_LISTING_RE = re.compile(
    r"\bsession (history|index|list|records?)\b|"
    r"\b(what|which|list|all|how many)\b.{0,30}\bsessions?\b|"
    r"\bsessions?\b.{0,25}\b(on record|do i have|history|so far|to date|recorded)\b|"
    r"\b(my|past|previous|recent|prior) sessions?\b|"
    r"\boverview of (my|your|the) sessions?\b",
    re.IGNORECASE,
)


def _rerank_band(results: List[Dict[str, Any]], query: str,
                 *, w_rel: float = 1.0, w_recency: float = 0.35, w_source: float = 0.6) -> List[Dict[str, Any]]:
    """Stage-2 feature rerank over the candidate band: relevance + recency + source-type.

    Query-intent aware: for "what sessions do I have on record" style queries, structured
    session sources (SESSION_INDEX rows, episodic summaries) get a strong source boost so
    they aren't buried by richer session-log prose that scores higher on raw cosine. For
    ordinary recall queries the source prior is small, so strong semantic matches still win
    — it only breaks near-ties (e.g. a slight preference for steward-approved episodics).
    """
    if not results:
        return results
    scores = [r.get("score", 0.0) for r in results]
    lo, hi = min(scores), max(scores)
    span = (hi - lo) or 1e-9
    listing = bool(_LISTING_RE.search(query or ""))
    dated = sorted({r["date"] for r in results if r.get("date")}, reverse=True)
    n = max(len(dated) - 1, 1)
    for r in results:
        rel = (r.get("score", 0.0) - lo) / span                  # 0..1 within the band
        d = r.get("date")
        rec = (1.0 - dated.index(d) / n) if (d and d in dated) else 0.0
        kind = r.get("kind", "")
        if listing and kind in ("session_index", "episodic"):
            src = 1.0                      # intent match: structured session sources lead
        elif kind == "knowledge_block":
            # Authoritative doctrinal source — a peer to episodic for concept queries,
            # but never leads a session-listing query (handled by the branch above).
            src = 0.0 if listing else 0.3
        elif kind == "episodic":
            src = 0.3                      # otherwise a small tie-breaker only
        elif kind == "session_index":
            src = 0.15
        else:
            src = 0.0
        r["rerank_score"] = round(w_rel * rel + w_recency * rec + w_source * src, 4)
    return sorted(results, key=lambda r: r["rerank_score"], reverse=True)


class SemanticMemoryIndex:
    """Loaded vector store with cosine search + stage-2 feature rerank."""

    def __init__(self, index: Dict[str, Any]):
        self.model = index["model"]
        self.dim = index["dim"]
        self.built_utc = index.get("built_utc", "")
        self._chunks = index["chunks"]
        self._matrix = [c["embedding"] for c in self._chunks]

    @classmethod
    def load(cls, path: Path = DEFAULT_INDEX_PATH) -> "SemanticMemoryIndex":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        candidate_k: int = 20,
        base_url: str = DEFAULT_BASE_URL,
        num_gpu: int = 0,
        max_excerpt: int = 600,
        timeout: int = 10,
        rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return the top_k chunks: stage-1 cosine over the corpus → candidate_k band →
        stage-2 feature rerank → top_k slice.

        Stage 2 (rerank=True) re-orders the band by relevance + recency + source-type,
        with query-intent awareness: a "what sessions do I have" query boosts structured
        session sources (SESSION_INDEX rows, episodic summaries) that pure cosine buries
        under richer prose. Local, deterministic, no extra model. See _rerank_band().
        timeout caps the query-embed call so a hung Ollama degrades fast.
        """
        if not self._chunks:
            return []
        qvec = _embed_query(query, model=self.model, base_url=base_url, num_gpu=num_gpu, timeout=timeout)
        sims = _cosine_matrix(self._matrix, qvec)
        order = sorted(range(len(self._chunks)), key=lambda i: float(sims[i]), reverse=True)
        band = order[:max(candidate_k, top_k)]
        results = []
        for rank, i in enumerate(band):
            c = self._chunks[i]
            results.append({
                "rank": rank,
                "score": round(float(sims[i]), 4),
                "source": c["source"],
                "kind": c["kind"],
                "date": c.get("date", ""),
                "excerpt": c["text"][:max_excerpt].strip(),
            })
        if rerank:
            results = _rerank_band(results, query)
        return results[:top_k]


# ---------------------------------------------------------------------------
# CLI — build / search for standalone testing
# ---------------------------------------------------------------------------

def _main(argv: List[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Eva semantic memory search")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="(re)build the vector index from the corpus")
    sp = sub.add_parser("search", help="query the index")
    sp.add_argument("query", nargs="+")
    sp.add_argument("--top-k", type=int, default=5)
    sp.add_argument("--candidate-k", type=int, default=20)
    args = ap.parse_args(argv)

    if args.cmd == "build":
        stats = build_index()
        print(json.dumps(stats, indent=2))
        return 0

    if args.cmd == "search":
        idx = SemanticMemoryIndex.load()
        q = " ".join(args.query)
        hits = idx.search(q, top_k=args.top_k, candidate_k=args.candidate_k)
        print(f"\nQuery: {q}\nIndex: {idx.count if hasattr(idx,'count') else len(idx._chunks)} chunks, model={idx.model}\n")
        for h in hits:
            print(f"  [{h['score']:.4f}] {h['source']} ({h['kind']}, {h['date']})")
            print(f"      {h['excerpt'][:240].replace(chr(10),' ')}")
        return 0
    return 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
