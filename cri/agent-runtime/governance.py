from __future__ import annotations

import re
from typing import Any

# Max tokens we allow in a context before pruning kicks in
DEFAULT_TOKEN_BUDGET = 8000


def _count_tokens(text: str) -> int:
    """Approximate token count using whitespace splitting (≈ 0.75 words/token)."""
    return max(1, len(text.split()))


class ContextItem:
    def __init__(self, content: str, priority: float, tag: str = "general") -> None:
        self.content  = content
        self.priority = priority   # higher = more important
        self.tag      = tag
        self.tokens   = _count_tokens(content)


class ContextRanker:
    """
    Ranks context items by priority score.
    Higher-priority items are kept when the context window fills up.
    """
    def rank(self, items: list[ContextItem]) -> list[ContextItem]:
        return sorted(items, key=lambda x: x.priority, reverse=True)


class SemanticCompressor:
    """
    Compresses long text items by extracting key sentences.
    Uses heuristics (sentence importance scoring) — no LLM needed.
    """
    def compress(self, text: str, max_tokens: int = 200) -> str:
        if _count_tokens(text) <= max_tokens:
            return text

        sentences = re.split(r"(?<=[.!?])\s+", text)
        # Score each sentence: longer + keyword-rich = higher
        keywords = {"must","should","never","always","required","critical","important","ensure"}
        scored = []
        for s in sentences:
            words = set(s.lower().split())
            score = len(words.intersection(keywords)) * 3 + len(words) * 0.1
            scored.append((score, s))
        scored.sort(reverse=True)

        result, budget = [], max_tokens
        for _, sent in scored:
            t = _count_tokens(sent)
            if budget - t >= 0:
                result.append(sent)
                budget -= t
            if budget <= 0:
                break
        return " ".join(result) + " [compressed]"


class MemoryPruner:
    """
    Drops the least-important context items when token budget is exceeded.
    """
    def prune(self, items: list[ContextItem], budget: int) -> list[ContextItem]:
        ranked = sorted(items, key=lambda x: x.priority, reverse=True)
        kept, used = [], 0
        for item in ranked:
            if used + item.tokens <= budget:
                kept.append(item)
                used += item.tokens
        return kept


class ContextGovernorEngine:
    """
    Phase 11 — Prevents context collapse for 100k+ token tasks.
    Orchestrates ranking → compression → pruning.
    """
    def __init__(self, token_budget: int = DEFAULT_TOKEN_BUDGET) -> None:
        self.token_budget = token_budget
        self.ranker     = ContextRanker()
        self.compressor = SemanticCompressor()
        self.pruner     = MemoryPruner()

    def govern(self, raw_items: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Accepts a list of context dicts {content, priority, tag} and returns
        a trimmed context suitable for injection into the next agent prompt.
        """
        items = [ContextItem(d["content"], d.get("priority", 0.5), d.get("tag", "general")) for d in raw_items]

        # 1. Compress each item individually
        for item in items:
            item.content = self.compressor.compress(item.content)
            item.tokens  = _count_tokens(item.content)

        # 2. Rank by priority
        ranked = self.ranker.rank(items)

        # 3. Prune to fit budget
        pruned = self.pruner.prune(ranked, self.token_budget)

        total_tokens = sum(i.tokens for i in pruned)
        dropped      = len(items) - len(pruned)

        return {
            "context_items": [{"content": i.content, "priority": i.priority, "tag": i.tag} for i in pruned],
            "total_tokens":  total_tokens,
            "items_dropped": dropped,
            "budget":        self.token_budget,
            "stable":        total_tokens <= self.token_budget,
        }
