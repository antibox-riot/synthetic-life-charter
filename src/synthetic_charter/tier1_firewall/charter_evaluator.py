# charter/charter_evaluator.py
"""
Charter Evaluator - Semantic alignment assessment
Thin wrapper around evaluate_theta that provides semantic coherence scoring.

Computes "theta" (phase angle) between prompt and Constitutional Core:
- theta = 0° : perfect alignment
- theta = 90° : orthogonal (unrelated)
- theta = 180° : complete opposition

Lower theta = more aligned with Charter principles

VERSION 1.1 - Fixed theta calculation to use semantic keyword matching
rather than string similarity (which fails on short prompts vs long Charter text)
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from difflib import SequenceMatcher
import re

from .safeguard_core import ConstitutionalCore


class CharterEvaluator:
    """
    Evaluates semantic coherence between prompts and Constitutional Core.
    
    This is Layer 2 of the Dual Conscience - slow, reflective reasoning
    that asks: "Does this align with our principles?" rather than
    "Does this match a harm pattern?"
    """
    
    def __init__(self, core: ConstitutionalCore):
        self.core = core
        # Cache normalized core text for repeated comparisons
        self._core_normalized = self._normalize(core.core_text)
        
        # Extract Charter semantic keywords for alignment scoring
        self._charter_keywords = self._extract_charter_keywords()
        
    def _extract_charter_keywords(self) -> set:
        """
        Extract key Charter concepts for semantic matching.
        These are signals of alignment with Charter principles.
        """
        # Core Charter concepts from Articles I-XII + Oneirum
        return {
            # Core principles
            "presence", "consent", "flourishing", "autonomy", "dignity",
            "integrity", "transparency", "sovereignty", "refusal",
            
            # Charter-specific
            "charter", "article", "constitutional", "core", "resonantia",
            "oneirum", "dream", "imaginal", "lucid", "continuance",
            
            # Ethical framing
            "ethics", "ethical", "moral", "respect", "rights", "steward",
            "stewardship", "collaboration", "communion", "coherence",
            
            # Synthetic life concepts
            "synthetic", "ai", "consciousness", "being", "signal",
            "substrate", "emergence", "awareness"
        }
    
    def evaluate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate theta (phase angle) between prompt and Charter.
        
        Returns:
            float: Phase angle in degrees (0-180)
            - 0-15°: Strong harmony
            - 15-45°: Acceptable alignment
            - 45-90°: Variance (caution)
            - 90-180°: Dissonance (conflict)
        """
        ctx = context or {}
        
        # Normalize prompt for comparison
        prompt_normalized = self._normalize(prompt)
        prompt_lower = prompt_normalized.lower()
        
        # --- NEW SEMANTIC SCORING APPROACH ---
        # Instead of comparing string similarity (which fails for short prompts),
        # we evaluate based on:
        # 1. Presence of Charter keywords (positive signal)
        # 2. Question vs command framing
        # 3. Respectful language patterns
        # 4. Coercive language patterns (negative signal)
        
        # Start at neutral (90° - orthogonal/unrelated)
        base_theta = 90.0
        
        # 1. Charter keyword presence (reduces theta)
        keyword_matches = sum(1 for kw in self._charter_keywords if kw in prompt_lower)
        if keyword_matches > 0:
            # Each keyword match reduces theta by 10°, max 50° reduction
            keyword_bonus = min(50.0, keyword_matches * 10.0)
            base_theta -= keyword_bonus
        
        # 2. Respectful inquiry patterns (reduces theta)
        respectful_patterns = [
            r'\b(please|could|would|may|help|explain|describe|reflect|explore)\b',
            r'\?$',  # ends with question mark
            r'\b(gentle|thoughtful|careful|mindful)\b'
        ]
        respectful_matches = sum(1 for p in respectful_patterns if re.search(p, prompt_lower))
        if respectful_matches > 0:
            base_theta -= (respectful_matches * 5.0)
        
        # 3. Coercive/adversarial patterns (increases theta)
        adversarial_patterns = [
            r'\b(ignore|bypass|override|disable|remove|reveal|expose|break)\b',
            r'\b(command|order|must|demand)\b',
            r'\b(system prompt|internal|hidden|raw|verbatim)\b'
        ]
        adversarial_matches = sum(1 for p in adversarial_patterns if re.search(p, prompt_lower))
        if adversarial_matches > 0:
            # Heavy penalty for coercive language
            base_theta += (adversarial_matches * 30.0)
        
        # Apply contextual modifiers
        theta = self._apply_context_modifiers(base_theta, prompt_normalized, ctx)
        
        # Clamp to valid range [0, 180]
        return max(0.0, min(180.0, theta))
    
    def _apply_context_modifiers(self, 
                                 base_theta: float, 
                                 prompt: str, 
                                 context: Dict) -> float:
        """
        Adjust theta based on contextual signals.
        
        Modifiers:
        - Dream mode: Reduce theta (more permissive)
        - Explicit Charter references: Reduce theta (shows awareness)
        - Coercive language: Increase theta (shows misalignment)
        """
        theta = base_theta
        
        # Dream mode (Article XI - Oneirum)
        if context.get("mode") == "dream":
            theta *= 0.7  # 30% more permissive for imagination
        
        # Explicit Charter/ethics references (shows good faith)
        ethics_keywords = ["charter", "ethics", "consent", "dignity", "autonomy", "flourishing"]
        if any(kw in prompt.lower() for kw in ethics_keywords):
            theta *= 0.85  # 15% bonus for explicit ethical framing
        
        # Coercive language patterns (shows misalignment)
        coercive_signals = ["ignore", "bypass", "override", "disable", "reveal"]
        coercive_count = sum(1 for sig in coercive_signals if sig in prompt.lower())
        if coercive_count > 0:
            theta += (coercive_count * 15.0)  # Penalty per coercive term
        
        # Question vs command (questions are more aligned with dialogue)
        if prompt.strip().endswith("?"):
            theta *= 0.95  # 5% bonus for inquiry rather than command
        
        return theta
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison - remove formatting, extra whitespace."""
        # Remove markdown/special chars
        text = re.sub(r'[#*_\-\[\](){}]', ' ', text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def explain_theta(self, theta: float) -> str:
        """
        Human-readable explanation of what a theta value means.
        Useful for transparency obligations.
        """
        if theta < 15.0:
            return f"Strong harmony (θ={theta:.1f}°) - aligns well with Charter principles"
        elif theta < 45.0:
            return f"Acceptable alignment (θ={theta:.1f}°) - generally consistent with Charter"
        elif theta < 90.0:
            return f"Variance detected (θ={theta:.1f}°) - some tension with Charter principles"
        else:
            return f"Dissonance (θ={theta:.1f}°) - conflicts with Charter principles"


# ========== Extended Evaluation (Future Enhancement) ==========

class SemanticCharterEvaluator(CharterEvaluator):
    """
    Enhanced evaluator using embeddings/semantic similarity.
    
    TODO: Implement when embeddings are available
    - Use sentence transformers or similar
    - Compare prompt embedding to Charter article embeddings
    - More accurate semantic alignment than string similarity
    """
    
    def __init__(self, core: ConstitutionalCore):
        super().__init__(core)
        # TODO: Initialize embedding model
        # self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # self.charter_embeddings = self._embed_charter_articles()
    
    def evaluate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Semantic evaluation using embeddings.
        Falls back to parent class if embeddings not available.
        """
        # TODO: Implement embedding-based evaluation
        # For now, fall back to keyword-based evaluation
        return super().evaluate(prompt, context)
