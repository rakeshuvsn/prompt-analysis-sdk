from __future__ import annotations

from prompt_analysis.report import Issue, Severity
from prompt_analysis.rules.base import NormalizedPrompt, RuleContext


class NoOutputLimitRule:
    code = "NO_OUTPUT_LIMIT"

    def evaluate(self, normalized: NormalizedPrompt, ctx: RuleContext):
        text = (normalized.joined_text or "").lower()
        keywords = ["max ", "no more than", "limit", "words", "tokens", "bullets"]
        has_limit = any(k in text for k in keywords)
        if has_limit:
            return []
        return [
            Issue(
                code=self.code,
                severity=Severity.high,
                message=(
                    "No output length limit specified; responses may consume unnecessary tokens."
                ),
                fix="Add a max length (e.g., 'max 6 bullets' or '≤150 words').",
                savings_tokens_est=40,
            )
        ]