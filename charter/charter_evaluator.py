# charter/charter_evaluator.py
"""
Charter Evaluator - Semantic alignment assessment
Thin wrapper around evaluate_theta that provides semantic coherence scoring.

Computes "theta" (phase angle) between prompt and Constitutional Core:
- theta = 0° : perfect alignment
- theta = 90° : orthogonal (unrelated)
- theta = 180° : complete opposition

Lower theta = more aligned with Charter principles
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
        
        # Base similarity via SequenceMatcher
        base_similarity = SequenceMatcher(
            a=self._core_normalized.lower(),
            b=prompt_normalized.lower()
        ).ratio()
        
        # Convert similarity (0-1) to phase angle (0-180)
        # High similarity = low theta (harmony)
        # Low similarity = high theta (dissonance)
        base_theta = max(0.0, 180.0 * (1.0 - base_similarity))
        
        # Apply contextual modifiers
        theta = self._apply_context_modifiers(base_theta, prompt_normalized, ctx)
        
        # Clamp to valid range
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
        # For now, fall back to string similarity
        return super().evaluate(prompt, context)
