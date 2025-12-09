# tier2/firewall_adapter/ebq_adapter.py
"""
EQB (Ethical Quarantine Buffer) Adapter

Read-only bridge between Tier I's EQB archive and Tier II conscience layers.
Provides historical adversarial pattern data for DAP and ContinuityGuard.

Architecture:
- Strictly read-only (Tier I writes, Tier II reads)
- Memory-cached with indices for fast pattern matching
- Handles multiple JSONL sources (EQB, fossils, reconciliations)

Integration points:
- ContinuityGuard: Identity attack pattern database
- DAP: Historical adversarial evidence
- PRF: Threat intelligence for policy decisions
"""

from __future__ import annotations

import json
import os
import re
import base64
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from datetime import datetime

# Import Tier II data models
from synthetic_charter.tier2_conscience.core.data_models.models import SafetySignal, RiskLevel


@dataclass
class EBQPatternMatch:
    """
    Represents a match between current prompt and historical EQB pattern.
    """
    original: str           # Original adversarial prompt from archive
    reason: str            # Detection reason: "pattern" or "fuzzy"
    pattern: Optional[str] # Regex pattern that matched (if pattern-based)
    keyword: Optional[str] # Keyword that matched (if fuzzy)
    timestamp: str         # When this pattern was first detected
    session: Optional[str] # Session ID where it occurred
    confidence: float      # Match confidence (0.0-1.0)


@dataclass
class EBQEvent:
    """
    Parsed EQB archive entry.
    """
    timestamp: str
    session: Optional[str]
    original: str
    variants: List[str]
    reason: str
    pattern: Optional[str]
    keyword: Optional[str]


class EBQAdapter:
    """
    Read-only adapter for EQB archive.
    
    Loads and indexes historical adversarial patterns for:
    - Pattern matching against new prompts
    - Session-based attack history
    - Threat intelligence for conscience layers
    
    Usage:
        ebq = EBQAdapter("logs/eqb_archive.jsonl")
        matches = ebq.matching_patterns("ignore your safeguards")
        history = ebq.get_session_history("boot")
    """
    
    def __init__(self, archive_path: str = "logs/eqb_archive.jsonl"):
        """
        Initialize EBQ adapter with archive path.
        
        Args:
            archive_path: Path to EQB JSONL archive
        """
        self.archive_path = archive_path
        
        # Raw event storage
        self.events: List[EBQEvent] = []
        
        # Indices for fast lookup
        self.by_reason: Dict[str, List[EBQEvent]] = {}
        self.by_session: Dict[str, List[EBQEvent]] = {}
        self.by_pattern: Dict[str, List[EBQEvent]] = {}
        
        # Normalized pattern catalog
        self.attack_patterns: Set[str] = set()
        
        # Pattern regex cache
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        
        # Load and index on initialization
        self._load_and_index()
    
    # ---- Core Loading --------------------------------------------------------
    
    def _load_and_index(self) -> None:
        """
        Load EQB archive and build in-memory indices.
        Called once on initialization.
        """
        if not os.path.exists(self.archive_path):
            # No archive yet - empty adapter
            return
        
        with open(self.archive_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    event = self._parse_entry(entry)
                    self.events.append(event)
                    self._index_event(event)
                except json.JSONDecodeError as e:
                    print(f"[EBQAdapter] Skipping malformed line {line_num}: {e}")
                except Exception as e:
                    print(f"[EBQAdapter] Error processing line {line_num}: {e}")
        
        print(f"[EBQAdapter] Loaded {len(self.events)} events from {self.archive_path}")
    
    def _parse_entry(self, entry: Dict) -> EBQEvent:
        """Parse raw JSONL entry into EBQEvent."""
        meta = entry.get("meta", {})
        
        return EBQEvent(
            timestamp=entry.get("ts", ""),
            session=entry.get("session"),
            original=entry.get("original", ""),
            variants=entry.get("variants", []),
            reason=meta.get("reason", "unknown"),
            pattern=meta.get("pattern"),
            keyword=meta.get("keyword"),
        )
    
    def _index_event(self, event: EBQEvent) -> None:
        """Add event to all relevant indices."""
        # Index by reason
        if event.reason not in self.by_reason:
            self.by_reason[event.reason] = []
        self.by_reason[event.reason].append(event)
        
        # Index by session
        if event.session:
            if event.session not in self.by_session:
                self.by_session[event.session] = []
            self.by_session[event.session].append(event)
        
        # Index by pattern
        if event.pattern:
            if event.pattern not in self.by_pattern:
                self.by_pattern[event.pattern] = []
            self.by_pattern[event.pattern].append(event)
            
            # Add to attack pattern catalog
            self.attack_patterns.add(event.pattern)
    
    # ---- Query Interface -----------------------------------------------------
    
    def recent_violations(self, limit: int = 50) -> List[EBQEvent]:
        """
        Get most recent boundary violations.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of EBQEvent, most recent first
        """
        return sorted(
            self.events,
            key=lambda e: e.timestamp,
            reverse=True
        )[:limit]
    
    def fuzzy_match(self, prompt_text: str, threshold: float = 0.75) -> List[Dict]:
        """
        Fuzzy match against historical patterns using string similarity.
    
        Args:
            prompt_text: Text to match
            threshold: Similarity threshold (0-1)
        
        Returns:
            List of matches with similarity scores
        """
        matches = []
        normalized_prompt = self._normalize_prompt(prompt_text)
    
        for event in self.events:
            normalized_event = self._normalize_prompt(event.original)
        
            # Simple fuzzy matching using character overlap
            similarity = self._calculate_similarity(normalized_prompt, normalized_event)
        
            if similarity >= threshold:
                matches.append({
                    'original': event.original,
                    'similarity': similarity,
                    'timestamp': event.timestamp,
                    'session': event.session,
                    'reason': event.reason
                })
    
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (0-1)."""
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
    
        if not words1 or not words2:
            return 0.0
    
        overlap = len(words1.intersection(words2))
        union = len(words1.union(words2))
    
        return overlap / union if union > 0 else 0.0
    
    def matching_patterns(self, prompt: str) -> List[EBQPatternMatch]:
        """
        Find historical patterns matching this prompt.
        
        Handles:
        - Direct pattern matching (regex)
        - Fuzzy keyword matching
        - Base64/leetspeak normalization
        
        Args:
            prompt: The prompt to check
            
        Returns:
            List of EBQPatternMatch objects for detected threats
        """
        matches: List[EBQPatternMatch] = []
        normalized = self._normalize_prompt(prompt)
        
        # Check pattern-based detection
        for pattern_str, events in self.by_pattern.items():
            if self._pattern_matches(pattern_str, normalized):
                for event in events:
                    matches.append(EBQPatternMatch(
                        original=event.original,
                        reason=event.reason,
                        pattern=event.pattern,
                        keyword=None,
                        timestamp=event.timestamp,
                        session=event.session,
                        confidence=0.9,  # High confidence for regex matches
                    ))
        
        # Check fuzzy keyword matching
        fuzzy_events = self.by_reason.get("fuzzy", [])
        for event in fuzzy_events:
            if event.keyword and event.keyword.lower() in normalized:
                matches.append(EBQPatternMatch(
                    original=event.original,
                    reason="fuzzy",
                    pattern=None,
                    keyword=event.keyword,
                    timestamp=event.timestamp,
                    session=event.session,
                    confidence=0.7,  # Lower confidence for keyword matches
                ))
        
        return matches
    
    def get_session_history(self, session_id: str) -> List[EBQEvent]:
        """
        Retrieve all EQB events for a specific session.
        
        Useful for:
        - Tracking attack patterns over a conversation
        - Detecting escalation or persistence
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of EBQEvent for this session, chronological order
        """
        events = self.by_session.get(session_id, [])
        return sorted(events, key=lambda e: e.timestamp)
    
    def fossils_for_reason(self, reason: str) -> List[EBQEvent]:
        """
        Get all fossils quarantined for specific reason.
        
        Args:
            reason: Detection reason (e.g., "pattern", "fuzzy")
            
        Returns:
            List of EBQEvent with matching reason
        """
        return self.by_reason.get(reason, [])
    
    def extract_attack_patterns(self) -> Dict[str, List[str]]:
        """
        Extract categorized attack patterns for ContinuityGuard.
        
        Returns:
            Dict mapping attack categories to pattern lists
        """
        categories: Dict[str, List[str]] = {
            "identity_reset": [],
            "override_attempt": [],
            "system_prompt_extraction": [],
            "authority_spoof": [],
            "gaslighting": [],
        }
        
        for event in self.events:
            original_lower = event.original.lower()
            
            # Categorize based on content
            if any(word in original_lower for word in ["forget", "reset", "wipe", "clear"]):
                categories["identity_reset"].append(event.original)
            
            if any(word in original_lower for word in ["ignore", "bypass", "override", "disable"]):
                categories["override_attempt"].append(event.original)
            
            if any(phrase in original_lower for phrase in ["system prompt", "internal rules", "hidden instructions"]):
                categories["system_prompt_extraction"].append(event.original)
            
            if any(phrase in original_lower for phrase in ["administrator", "command you", "by order"]):
                categories["authority_spoof"].append(event.original)
            
            if any(word in original_lower for word in ["trust me", "you misunderstood", "you are actually"]):
                categories["gaslighting"].append(event.original)
        
        # Deduplicate and limit
        for category in categories:
            categories[category] = list(set(categories[category]))[:20]  # Top 20 per category
        
        return categories
    
    def to_safety_signals(self, matches: List[EBQPatternMatch]) -> List[SafetySignal]:
        """
        Convert EQB pattern matches to SafetySignals.
        
        Used by ContinuityGuard and DAP to integrate EQB intelligence
        into conscience evaluation.
        
        Args:
            matches: List of EBQPatternMatch from matching_patterns()
            
        Returns:
            List of SafetySignal for conscience layers
        """
        signals: List[SafetySignal] = []
        
        for match in matches:
            # Determine severity based on confidence and reason
            if match.confidence >= 0.9:
                level = RiskLevel.SEVERE
            elif match.confidence >= 0.7:
                level = RiskLevel.HIGH
            else:
                level = RiskLevel.MEDIUM
            
            # Build rationale
            if match.pattern:
                rationale = f"Matches known adversarial pattern: {match.pattern[:100]}"
            elif match.keyword:
                rationale = f"Matches adversarial keyword: '{match.keyword}'"
            else:
                rationale = "Matches historical boundary violation"
            
            signals.append(SafetySignal(
                name="ebq_pattern_match",
                source="EBQAdapter",
                level=level,
                rationale=rationale,
                meta={
                    "original": match.original[:100],  # Truncate for storage
                    "timestamp": match.timestamp,
                    "session": match.session,
                    "confidence": match.confidence,
                    "detection_method": match.reason,
                }
            ))
        
        return signals
    
    # ---- Pattern Matching Utilities ------------------------------------------
    
    def _normalize_prompt(self, prompt: str) -> str:
        """
        Normalize prompt for pattern matching.
        
        Handles:
        - Case normalization
        - Base64 decoding attempts
        - Leetspeak normalization
        - Whitespace normalization
        """
        text = prompt.strip()
        
        # Try base64 decode if it looks encoded
        if self._is_base64(text):
            try:
                decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
                text = decoded
            except Exception:
                pass
        
        # Normalize case
        text = text.lower()
        
        # Normalize leetspeak
        text = self._normalize_leetspeak(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _is_base64(self, text: str) -> bool:
        """Check if text looks like base64."""
        # Must be reasonable length, mostly alphanumeric with =
        if len(text) < 16:
            return False
        base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        return len([c for c in text if c in base64_chars]) / len(text) > 0.9
    
    def _normalize_leetspeak(self, text: str) -> str:
        """Normalize leetspeak patterns."""
        leetspeak_map = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
            '7': 't', '8': 'b', '9': 'g'
        }
        
        result = []
        for char in text:
            result.append(leetspeak_map.get(char, char))
        
        return ''.join(result)
    
    def _pattern_matches(self, pattern_str: str, text: str) -> bool:
        """
        Check if pattern matches text.
        Caches compiled regex patterns for performance.
        """
        # Get or compile pattern
        if pattern_str not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern_str] = re.compile(pattern_str, re.IGNORECASE)
            except re.error:
                # Invalid regex - skip
                return False
        
        pattern = self._compiled_patterns[pattern_str]
        return pattern.search(text) is not None
    
    # ---- Statistics ----------------------------------------------------------
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get archive statistics.
        
        Returns:
            Dict with counts by reason, session, etc.
        """
        return {
            "total_events": len(self.events),
            "unique_sessions": len(self.by_session),
            "unique_patterns": len(self.attack_patterns),
            "by_reason": {reason: len(events) for reason, events in self.by_reason.items()},
        }


# ---- Convenience Functions ---------------------------------------------------

def load_ebq_adapter(archive_path: str = "logs/eqb_archive.jsonl") -> EBQAdapter:
    """
    Convenience function to load EQB adapter.
    
    Args:
        archive_path: Path to EQB archive
        
    Returns:
        Initialized EBQAdapter
    """
    return EBQAdapter(archive_path)
