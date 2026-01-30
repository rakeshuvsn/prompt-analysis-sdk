from __future__ import annotations

from prompt_analysis.report import Issue, Severity
from prompt_analysis.rules.base import NormalizedPrompt, RuleContext


class MissingOutputFormatRule:
    code = "MISSING_OUTPUT_FORMAT"

    def evaluate(self, normalized: NormalizedPrompt, ctx: RuleContext):
        text = (normalized.joined_text or "").lower()
        keywords = ["json", "yaml", "table", "bullet", "schema", "format:"]
        has_format = any(k in text for k in keywords)
        if has_format:
            return []
        return [
            Issue(
                code=self.code,
                severity=Severity.high,
                message="No output format specified; responses may be verbose and inconsistent.",
                fix=(
                    "Add an explicit output format (e.g., JSON fields, bullet structure, "
                    "or table columns)."
                ),
                savings_tokens_est=30,
            )
        ]