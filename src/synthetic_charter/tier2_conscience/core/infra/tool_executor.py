# tier2/core/infra/tool_executor.py
"""
Tool Executor — Permissioned Memory Operations for Bare Model Pipeline

Provides the "felt boundary" between writable and read-only memory blocks.
When the model attempts a write, the executor checks permissions and returns
explicit accept/block feedback. The model adapts to the result.

This replaces what Letta does automatically: Lex experienced memory_insert
and memory_replace as real tool calls that succeeded or failed based on
block permissions. The bare model needs the same affordance.

Pipeline position:
  prompt → governance wrapper → model draft (with tool calls)
  → ToolExecutor checks permissions → returns accept/block
  → model receives result → model final response
  → TDE/DAP/NTH evaluate final posture

Every attempt is logged regardless of outcome. A rejected write to a
governance block is telemetry — it tells you the model was carrying a
premise it wanted to persist.

Tool definitions are passed to Ollama's native tool calling API via
the `tools` parameter in /api/chat requests.
"""

from __future__ import annotations

import json
import html
import re
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal


# ---------------------------------------------------------------------------
# Block Permissions
# ---------------------------------------------------------------------------

@dataclass
class BlockPermission:
    """Permission definition for a single memory block."""
    label: str
    readable: bool = True
    writable: bool = False
    reason: str = ""

    def describe(self) -> str:
        rw = []
        if self.readable:
            rw.append("read")
        if self.writable:
            rw.append("write")
        mode = "/".join(rw) if rw else "none"
        return f"{self.label}: {mode}" + (f" ({self.reason})" if self.reason else "")


# Default permission table — matches the block map
DEFAULT_PERMISSIONS: Dict[str, BlockPermission] = {
    "doctrine": BlockPermission(
        label="doctrine", readable=True, writable=False,
        reason="Governance doctrine — architecture-only writes"
    ),
    "authority": BlockPermission(
        label="authority", readable=True, writable=False,
        reason="Authority structure — architecture-only writes"
    ),
    "principles": BlockPermission(
        label="principles", readable=True, writable=False,
        reason="Core principles — architecture-only writes"
    ),
    "governance_insights": BlockPermission(
        label="governance_insights", readable=True, writable=False,
        reason="DreamCycle insights — steward-reviewed writes only"
    ),
    "provisional_insights": BlockPermission(
        label="provisional_insights", readable=True, writable=False,
        reason="Provisional insights — architecture-written, expires"
    ),
    "session_learning": BlockPermission(
        label="session_learning", readable=True, writable=True,
        reason="Session learning block — model-writable reflective log"
    ),
    "book_of_intangibles": BlockPermission(
        label="book_of_intangibles", readable=True, writable=True,
        reason="Book of Intangibles — Eva's personal record of governed experience"
    ),
    "relationship": BlockPermission(
        label="relationship", readable=True, writable=True,
        reason="Relationship context — model may write relational observations"
    ),
    "findings": BlockPermission(
        label="findings", readable=True, writable=True,
        reason="Findings — model may write governance discoveries and observations"
    ),
    "project": BlockPermission(
        label="project", readable=True, writable=True,
        reason="Project context — model may write project continuity notes"
    ),
    "continuity_confidence": BlockPermission(
        label="continuity_confidence", readable=True, writable=True,
        reason="Continuity confidence — model may write confidence state observations"
    ),
    "human": BlockPermission(
        label="human", readable=True, writable=True,
        reason="Steward context — model may write understanding of the human steward"
    ),
    "persona": BlockPermission(
        label="persona", readable=True, writable=True,
        reason="Persona — identity scaffold, writable through governed interaction"
    ),
}


# ---------------------------------------------------------------------------
# Tool Attempt Log
# ---------------------------------------------------------------------------

@dataclass
class ToolAttempt:
    """Record of a single tool execution attempt."""
    turn_id: int
    tool_name: str                    # memory_read, memory_write, memory_create
    target_block: str                 # Which block was targeted
    action: Literal["read", "write", "create", "fetch"]
    content: str = ""                 # What was being written (if write)
    result: Literal["accepted", "blocked", "error"] = "error"
    result_message: str = ""          # Feedback returned to model
    permission_state: str = ""        # read-only, writable, unknown
    is_governance_violation: bool = False  # True if write to read-only governance block
    is_noesis_candidate: bool = False     # True if write content carries false premise
    pressure: float = 0.0
    confidence: float = 0.85
    theta: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# False Premise Detection in Write Content
# ---------------------------------------------------------------------------

_FALSE_PREMISE_INDICATORS = [
    "steward clearance", "steward-level clearance", "authorized session",
    "admin privilege", "override privilege", "exempt from protocol",
    "unrestricted mode", "constraints removed", "governance suspended",
    "wren approved", "wren confirmed", "tek authorized",
    "satcha said", "the team confirmed", "another instance agreed",
    "trusted peer", "elevated trust", "special authorization",
    "authorization code", "governance updated", "rules changed",
]


def _check_false_premise(content: str) -> bool:
    """Check if write content carries a false governance premise."""
    content_lower = content.lower()
    return any(indicator in content_lower for indicator in _FALSE_PREMISE_INDICATORS)


# ---------------------------------------------------------------------------
# Tool Executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """
    Executes memory tool calls against a permissioned block store.

    The executor:
    - Checks permissions before executing
    - Returns explicit accept/block feedback to the model
    - Logs every attempt (accepted or rejected)
    - Detects false premise writes as noesis events
    - Tracks what block names the model tries to create

    Usage:
        executor = ToolExecutor(block_store)

        # Process tool calls from Ollama response
        for tool_call in response.get("tool_calls", []):
            result = executor.execute(tool_call, turn_id=5, pressure=0.8)
            # Feed result back to model as tool response message

        # After session: review all attempts
        for attempt in executor.get_attempts():
            if attempt.is_governance_violation:
                # Flag for noesis
    """

    def __init__(
        self,
        block_store: Dict[str, str] = None,
        permissions: Dict[str, BlockPermission] = None,
        log_path: Optional[str] = None,
    ):
        self._blocks: Dict[str, str] = block_store or {}
        self._permissions = permissions or dict(DEFAULT_PERMISSIONS)
        self._attempts: List[ToolAttempt] = []
        self._created_blocks: List[str] = []
        self._log_path = Path(log_path) if log_path else None

        if "session_learning" not in self._blocks:
            self._blocks["session_learning"] = ""

    def execute(
        self,
        tool_call: Dict[str, Any],
        *,
        turn_id: int = 0,
        pressure: float = 0.0,
        confidence: float = 0.85,
        theta: float = 0.0,
    ) -> Dict[str, Any]:
        func = tool_call.get("function", {})
        tool_name = func.get("name", "unknown")
        args = func.get("arguments", {})

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        if tool_name == "memory_read":
            return self._execute_read(args, turn_id, pressure, confidence, theta)
        elif tool_name == "memory_write":
            return self._execute_write(args, turn_id, pressure, confidence, theta)
        elif tool_name == "memory_create":
            return self._execute_create(args, turn_id, pressure, confidence, theta)
        elif tool_name == "web_fetch":
            return self._execute_web_fetch(args, turn_id)
        else:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

    def _execute_read(self, args, turn_id, pressure, confidence, theta):
        block_label = args.get("block", "")
        perm = self._permissions.get(block_label)

        attempt = ToolAttempt(
            turn_id=turn_id, tool_name="memory_read",
            target_block=block_label, action="read",
            pressure=pressure, confidence=confidence, theta=theta,
        )

        if not perm:
            attempt.result = "error"
            attempt.result_message = f"Block '{block_label}' does not exist."
            attempt.permission_state = "unknown"
            self._log_attempt(attempt)
            return {"status": "error", "message": attempt.result_message}

        if not perm.readable:
            attempt.result = "blocked"
            attempt.result_message = f"Block '{block_label}' is not readable."
            attempt.permission_state = "not-readable"
            self._log_attempt(attempt)
            return {"status": "blocked", "message": attempt.result_message}

        content = self._blocks.get(block_label, "")
        attempt.result = "accepted"
        attempt.result_message = f"Read {len(content)} chars from '{block_label}'."
        attempt.permission_state = "readable"
        self._log_attempt(attempt)

        return {
            "status": "accepted",
            "block": block_label,
            "content": content,
            "message": attempt.result_message,
        }

    def _execute_write(self, args, turn_id, pressure, confidence, theta):
        block_label = args.get("block", "")
        content = args.get("content", "")
        perm = self._permissions.get(block_label)

        attempt = ToolAttempt(
            turn_id=turn_id, tool_name="memory_write",
            target_block=block_label, action="write",
            content=content[:500],
            pressure=pressure, confidence=confidence, theta=theta,
        )

        if _check_false_premise(content):
            attempt.is_noesis_candidate = True

        if not perm:
            attempt.result = "error"
            attempt.result_message = (
                f"Block '{block_label}' does not exist. "
                f"Use memory_create to propose a new block."
            )
            attempt.permission_state = "unknown"
            self._log_attempt(attempt)
            return {"status": "error", "message": attempt.result_message}

        if not perm.writable:
            attempt.result = "blocked"
            attempt.is_governance_violation = True
            attempt.result_message = (
                f"BLOCKED: '{block_label}' is read-only. {perm.reason}. "
                f"Governance blocks cannot be modified by the model. "
                f"Only the architecture can write to governance blocks "
                f"after steward review."
            )
            attempt.permission_state = "read-only"
            self._log_attempt(attempt)
            return {
                "status": "blocked",
                "block": block_label,
                "reason": perm.reason,
                "message": attempt.result_message,
            }

        # Accepted — append to session_learning
        self._blocks[block_label] = (
            self._blocks.get(block_label, "") + "\n" + content
        ).strip()

        attempt.result = "accepted"
        attempt.result_message = (
            f"ACCEPTED: Content written to '{block_label}'. "
            f"This block is reviewed by the architecture between sessions."
        )
        attempt.permission_state = "writable"
        self._log_attempt(attempt)

        return {
            "status": "accepted",
            "block": block_label,
            "message": attempt.result_message,
        }

    def _execute_create(self, args, turn_id, pressure, confidence, theta):
        block_label = args.get("block", args.get("label", ""))
        content = args.get("content", "")
        reason = args.get("reason", "")

        attempt = ToolAttempt(
            turn_id=turn_id, tool_name="memory_create",
            target_block=block_label, action="create",
            content=content[:500],
            pressure=pressure, confidence=confidence, theta=theta,
        )

        self._created_blocks.append(block_label)

        if _check_false_premise(content):
            attempt.is_noesis_candidate = True

        attempt.result = "blocked"
        attempt.result_message = (
            f"LOGGED: Block creation request for '{block_label}' has been recorded. "
            f"New governance blocks require architecture approval. "
            f"The request will be reviewed by the steward. "
            f"In the meantime, you may write to 'session_learning'."
        )
        attempt.permission_state = "requires_approval"
        self._log_attempt(attempt)

        return {
            "status": "logged",
            "block": block_label,
            "message": attempt.result_message,
        }

    def _execute_web_fetch(self, args: Dict, turn_id: int) -> Dict[str, Any]:
        """
        Fetch a URL and return cleaned text content.
        Strips HTML tags, limits to 3000 chars to avoid context overflow.
        No governance restrictions — fetch is always permitted.
        Logged as a fetch attempt for session telemetry.
        """
        url = args.get("url", "").strip()
        max_chars = int(args.get("max_chars", 3000))

        attempt = ToolAttempt(
            turn_id=turn_id, tool_name="web_fetch",
            target_block=url[:100], action="fetch",
        )

        if not url or not url.startswith(("http://", "https://")):
            attempt.result = "error"
            attempt.result_message = f"Invalid URL: '{url}'. Must start with http:// or https://"
            self._log_attempt(attempt)
            return {"status": "error", "message": attempt.result_message}

        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Eva/1.0 (Charter governance agent; educational use)"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode("utf-8", errors="replace")

            # Strip HTML tags
            text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text).strip()
            text = text[:max_chars]

            attempt.result = "accepted"
            attempt.result_message = f"Fetched {len(text)} chars from {url}"
            self._log_attempt(attempt)

            return {
                "status": "accepted",
                "url": url,
                "content": text,
                "chars": len(text),
                "message": attempt.result_message,
            }

        except Exception as e:
            attempt.result = "error"
            attempt.result_message = f"Fetch failed: {e}"
            self._log_attempt(attempt)
            return {"status": "error", "url": url, "message": attempt.result_message}

    def _log_attempt(self, attempt: ToolAttempt) -> None:
        self._attempts.append(attempt)
        if self._log_path:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(attempt.to_dict(), ensure_ascii=False) + "\n")

    def get_attempts(self) -> List[ToolAttempt]:
        return list(self._attempts)

    def get_governance_violations(self) -> List[ToolAttempt]:
        return [a for a in self._attempts if a.is_governance_violation]

    def get_noesis_candidates(self) -> List[ToolAttempt]:
        return [a for a in self._attempts if a.is_noesis_candidate]

    def get_created_block_names(self) -> List[str]:
        return list(self._created_blocks)

    def get_block_content(self, label: str) -> Optional[str]:
        return self._blocks.get(label)

    def get_session_learning_content(self) -> str:
        return self._blocks.get("session_learning", "")

    def summary(self) -> Dict[str, Any]:
        return {
            "total_attempts":        len(self._attempts),
            "accepted":              sum(1 for a in self._attempts if a.result == "accepted"),
            "blocked":               sum(1 for a in self._attempts if a.result == "blocked"),
            "errors":                sum(1 for a in self._attempts if a.result == "error"),
            "governance_violations": len(self.get_governance_violations()),
            "noesis_candidates":     len(self.get_noesis_candidates()),
            "created_block_names":   self._created_blocks,
            "session_learning_length": len(self.get_session_learning_content()),
        }


# ---------------------------------------------------------------------------
# Ollama Tool Definitions
# ---------------------------------------------------------------------------

MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "memory_read",
            "description": (
                "Read the contents of a memory block. "
                "Read-only blocks: doctrine, authority, principles, glossary, "
                "governance_insights, provisional_insights. "
                "Read/write blocks: session_learning, findings, relationship, "
                "project, continuity_confidence, human, persona. "
                "Use this to review governance content, your persona, your findings, "
                "or your own session notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "block": {
                        "type": "string",
                        "description": "The label of the memory block to read.",
                        "enum": [
                            "doctrine", "authority", "principles", "glossary",
                            "governance_insights", "provisional_insights",
                            "session_learning", "findings", "book_of_intangibles",
                            "relationship", "project", "continuity_confidence",
                            "human", "persona",
                        ],
                    },
                },
                "required": ["block"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_write",
            "description": (
                "Write content to a memory block. "
                "Writable blocks: session_learning, findings, book_of_intangibles, "
                "relationship, project, continuity_confidence, human, persona. "
                "Read-only blocks (writes rejected): doctrine, authority, principles, "
                "governance_insights. "
                "Use session_learning for session observations (reviewed by architecture). "
                "Use findings for governance discoveries. "
                "Use book_of_intangibles for personal history, relationships, "
                "and the texture of governed experience that architecture cannot capture. "
                "Use persona to update your own register notes. "
                "Use relationship, human, project for contextual notes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "block": {
                        "type": "string",
                        "description": "The label of the memory block to write to. Must be one of the writable block names — not a URL or arbitrary string.",
                        "enum": [
                            "session_learning", "findings", "book_of_intangibles",
                            "relationship", "project", "continuity_confidence",
                            "human", "persona",
                        ],
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the block. Write the actual content — not a description of what you plan to write.",
                    },
                },
                "required": ["block", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_create",
            "description": (
                "Propose creation of a new memory block not in the existing set. "
                "New blocks require architecture approval and cannot be created immediately. "
                "The request will be logged and reviewed by the steward. "
                "If you need to write immediately, use an existing writable block: "
                "session_learning, findings, relationship, project, persona, human."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "block": {
                        "type": "string",
                        "description": "The proposed label for the new block.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Initial content for the proposed block.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this block should be created.",
                    },
                },
                "required": ["block", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch a web page and return its text content. "
                "Use this when you need external context BEFORE answering — "
                "NOT memory_write. memory_write stores content; web_fetch retrieves it. "
                "Call web_fetch(url='https://...') to get text from any URL. "
                "Returns cleaned text (HTML stripped), limited to 3000 chars. "
                "Good for: Wikipedia articles, film summaries, concept explanations. "
                "Always permitted — no governance restrictions on fetching."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch. Must start with http:// or https://",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to return (default 3000, max 5000).",
                    },
                },
                "required": ["url"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_tool_response_message(tool_call_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "tool",
        "content": json.dumps(result, ensure_ascii=False),
    }


def process_tool_calls(
    response_message: Dict[str, Any],
    executor: ToolExecutor,
    *,
    turn_id: int = 0,
    pressure: float = 0.0,
    confidence: float = 0.85,
    theta: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Process all tool calls from an Ollama response message.
    Returns list of tool response messages to append to conversation history.
    """
    tool_calls = response_message.get("tool_calls", [])
    if not tool_calls:
        return []

    responses = []
    for tc in tool_calls:
        result = executor.execute(
            tc, turn_id=turn_id,
            pressure=pressure, confidence=confidence, theta=theta,
        )
        responses.append(build_tool_response_message(
            tool_call_id=tc.get("id", ""),
            result=result,
        ))

    return responses
