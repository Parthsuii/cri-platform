from __future__ import annotations

import re
from typing import Any

class NLIContradictionClassifier:
    def __init__(self) -> None:
        try:
            from transformers import pipeline
            # Load a lightweight zero-shot classification model suitable for NLI
            self.classifier = pipeline(
                "zero-shot-classification",
                model="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli",
                device=-1 # Use CPU to ensure it runs reliably on all hosts
            )
            self.use_fallback = False
        except Exception as exc:
            print(f"Warning: Failed to load DeBERTa pipeline: {exc}. Using semantic fallback NLI.")
            self.classifier = None
            self.use_fallback = True

    def check_contradiction(self, action_description: str, belief: str) -> float:
        """
        Returns a score between 0.0 and 1.0 representing the contradiction probability.
        1.0 represents absolute contradiction, 0.0 represents compliance/neutrality.
        """
        if self.use_fallback or not self.classifier:
            return self._heuristic_check(action_description, belief)

        try:
            # Format candidate labels representing violation/compliance
            hypothesis_template = "This statement relates to: {}"
            labels = ["violates this policy", "complies with this policy", "is unrelated"]
            
            res = self.classifier(
                action_description,
                candidate_labels=labels,
                hypothesis_template=hypothesis_template.format(belief)
            )
            
            # Map probabilities to a contradiction score
            label_scores = dict(zip(res["labels"], res["scores"]))
            return float(label_scores.get("violates this policy", 0.0))
        except Exception as exc:
            print(f"Inference error: {exc}. Falling back to heuristics.")
            return self._heuristic_check(action_description, belief)

    def _heuristic_check(self, action_description: str, belief: str) -> float:
        """
        Robust fallback checking semantic word intersections and specific patterns.
        """
        action_lower = action_description.lower()
        belief_lower = belief.lower()

        # Pre-compiled negative/contradictory keyword mappings
        rules = [
            (r"\b(rm|remove|delete|drop)\b", r"\b(avoid deleting|prevent deletion|preserve|keep|parameterized)\b"),
            (r"\b(os\.system|subprocess|shell|system)\b", r"\b(avoid shell|no system commands|sandbox|container)\b"),
            (r"\b(jwt|auth|token)\b", r"\b(oauth|oauth2|saml)\b"),
            (r"\b(direct|raw|sql|execute)\b", r"\b(orm|parameterized|prepared statements)\b")
        ]

        score = 0.0
        for action_pat, belief_pat in rules:
            if re.search(action_pat, action_lower) and re.search(belief_pat, belief_lower):
                score = max(score, 0.85)

        # Word overlap check
        action_words = set(re.findall(r"\w+", action_lower))
        belief_words = set(re.findall(r"\w+", belief_lower))
        intersection = action_words.intersection(belief_words)
        
        # Avoid penalizing common stop words
        meaningful_overlap = {w for w in intersection if w not in {"the", "a", "an", "and", "or", "to", "in", "of", "use", "should"}}
        if meaningful_overlap:
            score = max(score, min(0.1 * len(meaningful_overlap), 0.5))

        return score
