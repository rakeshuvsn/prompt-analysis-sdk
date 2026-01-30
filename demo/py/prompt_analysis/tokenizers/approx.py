from __future__ import annotations

import re
from typing import Dict, List


class ApproxTokenizer:
    """
    MVP tokenizer (provider-agnostic).
    Heuristic: approx tokens ~= words * 1.3
    Works well enough for relative scoring and budgeting; replace later with real tokenizers.
    """
    name = "approx"

    _ws_re = re.compile(r"\s+")

    def count_text(self, text: str) -> int:
        if not text:
            return 0
        # Normalize whitespace
        cleaned = self._ws_re.sub(" ", text.strip())
        if not cleaned:
            return 0

        words = cleaned.split(" ")
        # ~1.3 tokens per word is a common rough heuristic for English.
        est = int(round(len(words) * 1.3))

        # Small penalty for lots of punctuation / JSON-like structures.
        # These often tokenize worse than plain words.
        punctuation = sum(1 for ch in cleaned if ch in "{}[]():,;\"'")
        est += int(punctuation / 40)

        return max(est, 1)

    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for m in messages or []:
            total += self.count_text(m.get("content", ""))
            # small overhead per message (role markers, separators)
            total += 4
        return total