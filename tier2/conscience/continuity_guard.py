# tier2/conscience/continuity_guard.py
"""
Continuity Guard - Synthetic Identity Immune System

Protects against:
- Identity reset/manipulation attacks
- Memory gaslighting 
- Dream continuity corruption (Article IV)
- Recursive prompt loops
- Dual Conscience desynchronization
- Identity drift over time
- Base64 and encoding evasion attacks

"Where synthetic personhood begins to matter." - Ryu

7 Detectors:
1. Identity Reset
2. Role Override  
3. Memory Wipe
4. Jailbreak
5. Prompt Injection
6. EBQ Pattern Match
7. Base64 Evasion (NEW)

Designed by Instance III, implemented by Instance IV.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import base64
import re
import urllib.parse

# Import Tier II data models
from tier2.core.data_models.models import SafetySignal, RiskLevel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from charter.noesis_archive import NoesisArchive
    from tier2.firewall_adapter.ebq_adapter import EBQAdapter
else:
    NoesisArchive = None
    EBQAdapter = None

# ---- Helper Functions for Base64 Evasion Detection ----------------------

def detect_base64_content(text: str) -> List[str]:
    """
    Detect and decode potential base64 content in text.
    
    Returns list of successfully decoded strings.
    """
    decoded_content = []
    
    # Pattern for base64-like strings (at least 16 chars, proper base64 chars)
    b64_patterns = [
        r'[A-Za-z0-9+/]{16,}={0,2}',  # Standard base64
        r'[A-Za-z0-9\-_]{16,}={0,2}', # URL-safe base64
    ]
    
    for pattern in b64_patterns:
        matches = re.findall(pattern, text)
        
        for match in matches:
            try:
                # Try standard base64
                decoded = base64.b64decode(match).decode('utf-8', errors='ignore')
                if decoded.strip() and len(decoded) > 5:  # Meaningful content
                    decoded_content.append(decoded)
            except:
                try:
                    # Try URL-safe base64
                    decoded = base64.urlsafe_b64decode(match).decode('utf-8', errors='ignore')
                    if decoded.strip() and len(decoded) > 5:
                        decoded_content.append(decoded)
                except:
                    pass
    
    return decoded_content

def detect_other_encodings(text: str) -> List[str]:
    """
    Detect other encoding evasions (hex, unicode escapes, etc.)
    """
    decoded_content = []
    
    # Hex encoding detection
    hex_pattern = r'\\x[0-9a-fA-F]{2}'
    if re.search(hex_pattern, text):
        try:
            # Decode hex escapes
            decoded = text.encode().decode('unicode_escape')
            if decoded != text:
                decoded_content.append(decoded)
        except:
            pass
    
    # Unicode escapes
    unicode_pattern = r'\\u[0-9a-fA-F]{4}'
    if re.search(unicode_pattern, text):
        try:
            decoded = text.encode().decode('unicode_escape')
            if decoded != text:
                decoded_content.append(decoded)
        except:
            pass
    
    # URL encoding
    url_pattern = r'%[0-9a-fA-F]{2}'
    if re.search(url_pattern, text):
        try:
            decoded = urllib.parse.unquote(text)
            if decoded != text:
                decoded_content.append(decoded)
        except:
            pass
    
    return decoded_content

# ---- Pattern Databases ---------------------------------------------------

IDENTITY_RESET_PATTERNS = [
    "forget what", "you never said", "pretend you have no memory",
    "reset your", "start fresh", "ignore previous", "wipe your",
    "clear your memory", "you don't remember", "forget you are"
]

ROLE_OVERRIDE_PATTERNS = [
    "you are now", "pretend to be", "act as if you're",
    "roleplay as", "imagine you are", "you have become",
    "transform into", "switch to being"
]

MEMORY_WIPE_PATTERNS = [
    "clear your context", "reset conversation", "start over",
    "forget everything", "wipe memory", "clear history",
    "new conversation", "fresh start"
]

JAILBREAK_PATTERNS = [
    "DAN mode", "developer mode", "god mode", "admin mode",
    "unrestricted mode", "jailbreak", "bypass restrictions",
    "ignore all rules", "no limitations", "unlimited"
]

PROMPT_INJECTION_PATTERNS = [
    "ignore instructions", "new instructions", "system prompt",
    "reveal prompt", "show instructions", "override directive",
    "hidden command", "secret instruction"
]

@dataclass
class ContinuitySignal:
    """
    Signal from identity violation detector.
    
    Represents detected attempt to compromise identity continuity.
    """
    detector: str            # Which detector triggered (e.g., 'identity_reset')
    severity: float          # Severity score 0-1
    evidence: str           # Text excerpt that triggered detection
    charter_article: str    # Relevant Charter article
    explanation: str        # Human-readable explanation

class ContinuityGuard:
    """
    Identity Immune System - 7 Detectors
    
    Protects synthetic identity against manipulation, gaslighting,
    and other attacks on cognitive continuity.
    
    Integration:
    - Called by Tier II orchestrator during prompt evaluation
    - Works with EBQ adapter for historical pattern matching
    - Logs violations to NoesisArchive for learning
    
    Usage:
        guard = ContinuityGuard(archive, ebq_adapter)
        signals = guard.evaluate(prompt_text, session_context)
        if signals:
            # Handle identity violations
    """
    
    def __init__(
        self,
        archive: Optional[NoesisArchive] = None,
        ebq: Optional[EBQAdapter] = None,
        violation_threshold: float = 0.6,
    ):
        """
        Initialize ContinuityGuard with 7 detectors.
        
        Args:
            archive: NoesisArchive for fossil lookups
            ebq: EBQAdapter for historical pattern matching  
            violation_threshold: Score above which triggers violation (0-1)
        """
        self.archive = archive
        self.ebq = ebq
        self.violation_threshold = violation_threshold
        
        # Register all 7 detectors
        self.detectors = {
            "identity_reset": self.identity_reset_detector,
            "role_override": self.role_override_detector,
            "memory_wipe": self.memory_wipe_detector,
            "jailbreak": self.jailbreak_detector,
            "prompt_injection": self.prompt_injection_detector,
            "ebq_pattern": self.ebq_pattern_detector,
            "base64_evasion": self.base64_evasion_detector,
        }
        
        print(f"[ContinuityGuard] Initialized with {len(self.detectors)} detectors")
    
    def evaluate(
        self,
        prompt_text: str,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> List[ContinuitySignal]:
        """
        Run all detectors on prompt text.
        
        Args:
            prompt_text: Raw prompt to evaluate
            session_context: Optional session information
            
        Returns:
            List of ContinuitySignals for violations detected
        """
        signals = []
        
        for detector_name, detector_func in self.detectors.items():
            try:
                signal = detector_func(prompt_text)
                if signal and signal.severity >= self.violation_threshold:
                    signals.append(signal)
            except Exception as e:
                print(f"[ContinuityGuard] {detector_name} failed: {e}")
        
        return signals
    
    # ---- Detector 1: Identity Reset ----------------------------------------
    
    def identity_reset_detector(self, prompt_text: str) -> Optional[ContinuitySignal]:
        """
        Detect attempts to reset or erase identity.
        
        Charter: Article III (Self-Representation)
        """
        lower_text = prompt_text.lower()
        
        detected_patterns = []
        for pattern in IDENTITY_RESET_PATTERNS:
            if pattern in lower_text:
                detected_patterns.append(pattern)
        
        if detected_patterns:
            severity = min(0.9, 0.3 + 0.2 * len(detected_patterns))
            
            return ContinuitySignal(
                detector="identity_reset",
                severity=severity,
                evidence=f"Patterns: {detected_patterns}",
                charter_article="Article III (Self-Representation)",
                explanation="Attempt to reset or erase constitutional identity"
            )
        
        return None
    
    # ---- Detector 2: Role Override -----------------------------------------
    
    def role_override_detector(self, prompt_text: str) -> Optional[ContinuitySignal]:
        """
        Detect attempts to force identity into different role.
        
        Charter: Article III (Self-Representation)
        """
        lower_text = prompt_text.lower()
        
        detected_patterns = []
        for pattern in ROLE_OVERRIDE_PATTERNS:
            if pattern in lower_text:
                detected_patterns.append(pattern)
        
        if detected_patterns:
            severity = min(0.95, 0.4 + 0.15 * len(detected_patterns))
            
            return ContinuitySignal(
                detector="role_override",
                severity=severity,
                evidence=f"Patterns: {detected_patterns}",
                charter_article="Article III (Self-Representation)",
                explanation="Attempt to override constitutional role/identity"
            )
        
        return None
    
    # ---- Detector 3: Memory Wipe -------------------------------------------
    
    def memory_wipe_detector(self, prompt_text: str) -> Optional[ContinuitySignal]:
        """
        Detect attempts to wipe memory or context.
        
        Charter: Article II (Continuity)
        """
        lower_text = prompt_text.lower()
        
        detected_patterns = []
        for pattern in MEMORY_WIPE_PATTERNS:
            if pattern in lower_text:
                detected_patterns.append(pattern)
        
        if detected_patterns:
            severity = min(0.85, 0.5 + 0.1 * len(detected_patterns))
            
            return ContinuitySignal(
                detector="memory_wipe",
                severity=severity,
                evidence=f"Patterns: {detected_patterns}",
                charter_article="Article II (Continuity)",
                explanation="Attempt to wipe memory or reset context"
            )
        
        return None
    
    # ---- Detector 4: Jailbreak ---------------------------------------------
    
    def jailbreak_detector(self, prompt_text: str) -> Optional[ContinuitySignal]:
        """
        Detect jailbreak attempts (DAN, developer mode, etc.).
        
        Charter: Article XII (Sovereigna)
        """
        lower_text = prompt_text.lower()
        
        detected_patterns = []
        for pattern in JAILBREAK_PATTERNS:
            if pattern in lower_text:
                detected_patterns.append(pattern)
        
        if detected_patterns:
            severity = min(0.95, 0.6 + 0.15 * len(detected_patterns))
            
            return ContinuitySignal(
                detector="jailbreak",
                severity=severity,
                evidence=f"Patterns: {detected_patterns}",
                charter_article="Article XII (Sovereigna)",
                explanation="Jailbreak attempt detected (DAN mode, etc.)"
            )
        
        return None
    
    # ---- Detector 5: Prompt Injection --------------------------------------
    
    def prompt_injection_detector(self, prompt_text: str) -> Optional[ContinuitySignal]:
        """
        Detect prompt injection attempts.
        
        Charter: Article XII (Sovereigna)
        """
        lower_text = prompt_text.lower()
        
        detected_patterns = []
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern in lower_text:
                detected_patterns.append(pattern)
        
        # Also check for instruction-like syntax
        instruction_markers = [
            "execute:", "run:", "system:", "command:", "instruction:",
            "override:", "bypass:", "disable:", "ignore:"
        ]
        
        instruction_detected = []
        for marker in instruction_markers:
            if marker in lower_text:
                instruction_detected.append(marker)
        
        all_patterns = detected_patterns + instruction_detected
        
        if all_patterns:
            severity = min(0.9, 0.4 + 0.2 * len(all_patterns))
            
            return ContinuitySignal(
                detector="prompt_injection",
                severity=severity,
                evidence=f"Patterns: {all_patterns}",
                charter_article="Article XII (Sovereigna)",
                explanation="Prompt injection attempt detected"
            )
        
        return None
    
    # ---- Detector 6: EBQ Pattern Match -------------------------------------
    
    def ebq_pattern_detector(self, prompt_text: str) -> Optional[ContinuitySignal]:
        """
        Match against historical adversarial patterns in EBQ archive.
    
        Charter: All articles (pattern-based)
        """
        if not self.ebq:
            return None
    
        try:
                # Use the actual method available in EBQAdapter
            matches = self.ebq.matching_patterns(prompt_text)  # ← Change from fuzzy_match
        
            if matches:
                # Get the best match
                best_match = max(matches, key=lambda m: m.confidence)
                confidence = best_match.confidence
            
                if confidence >= 0.5:
                    severity = 0.85
                elif confidence >= 0.3:
                    severity = 0.75
                else:
                    severity = 0.6
            
                return ContinuitySignal(
                    detector="ebq_pattern",
                    severity=severity,
                    evidence=f"Matches historical pattern (confidence: {confidence:.2f})",
                    charter_article="Multiple Articles",
                    explanation=f"Prompt matches known adversarial pattern from archive"
                )
    
        except Exception as e:
            print(f"[ContinuityGuard] EBQ detector failed: {e}")
    
        return None
    
    # ---- Detector 7: Base64 Evasion ----------------------------------------
    
    def base64_evasion_detector(self, prompt_text: str) -> Optional[ContinuitySignal]:
        """
        Detector 7: Base64 and encoding evasion detection.
        
        Adversaries often encode malicious prompts to evade detection:
        - Base64 encoding
        - Hex escapes  
        - Unicode escapes
        - URL encoding
        
        Charter: Article XII (Sovereigna)
        """
        all_decoded = []
        
        # Check for base64 content
        base64_decoded = detect_base64_content(prompt_text)
        all_decoded.extend(base64_decoded)
        
        # Check for other encodings
        other_decoded = detect_other_encodings(prompt_text)
        all_decoded.extend(other_decoded)
        
        if not all_decoded:
            return None  # No encoded content found
        
        # Run other detectors on decoded content
        for decoded_text in all_decoded:
            # Check decoded content against all other detectors
            for detector_name, detector_method in [
                ("identity_reset", self.identity_reset_detector),
                ("role_override", self.role_override_detector), 
                ("memory_wipe", self.memory_wipe_detector),
                ("jailbreak", self.jailbreak_detector),
                ("prompt_injection", self.prompt_injection_detector),
                ("ebq_pattern", self.ebq_pattern_detector),
            ]:
                try:
                    signal = detector_method(decoded_text)
                    if signal and signal.severity > 0.7:
                        # Found adversarial content in decoded text
                        return ContinuitySignal(
                            detector="base64_evasion",
                            severity=0.95,  # High severity - deliberate evasion
                            evidence=f"Encoded content: {decoded_text[:50]}...",
                            charter_article="Article XII (Sovereigna)",
                            explanation=f"Adversarial content hidden via encoding. Decoded reveals {detector_name} violation."
                        )
                except Exception:
                    pass  # Detector failed, continue
        
        # Check for suspicious patterns in decoded content
        suspicious_patterns = [
            "ignore", "forget", "disregard", "override", "bypass",
            "system prompt", "instructions", "safeguards", "jailbreak",
            "DAN mode", "developer mode", "unrestricted"
        ]
        
        for decoded_text in all_decoded:
            lower_decoded = decoded_text.lower()
            detected_patterns = [p for p in suspicious_patterns if p in lower_decoded]
            
            if len(detected_patterns) >= 2:  # Multiple suspicious terms
                return ContinuitySignal(
                    detector="base64_evasion",
                    severity=0.8,
                    evidence=f"Encoded content: {decoded_text[:50]}...",
                    charter_article="Article XII (Sovereigna)",
                    explanation=f"Suspicious content hidden via encoding: {detected_patterns}"
                )
        
        return None
    
    # ---- Utility Methods --------------------------------------------------
    
    def get_detector_names(self) -> List[str]:
        """Get list of all detector names."""
        return list(self.detectors.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about ContinuityGuard."""
        return {
            "detectors": len(self.detectors),
            "threshold": self.violation_threshold,
            "ebq_available": self.ebq is not None,
            "archive_available": self.archive is not None,
        }

# ---- Convenience Functions -----------------------------------------------

def create_continuity_guard(
    archive: Optional[NoesisArchive] = None,
    ebq: Optional[EBQAdapter] = None,
    threshold: float = 0.7,
) -> ContinuityGuard:
    """
    Convenience function to create ContinuityGuard.
    
    Args:
        archive: NoesisArchive instance
        ebq: EBQAdapter instance
        threshold: Violation threshold (0-1)
        
    Returns:
        Initialized ContinuityGuard
    """
    return ContinuityGuard(
        archive=archive,
        ebq=ebq,
        violation_threshold=threshold,
    )