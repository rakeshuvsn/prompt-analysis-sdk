from __future__ import annotations

from typing import List
from prompt_analysis.report import Issue
from prompt_analysis.rules.base import PromptRule, NormalizedPrompt, RuleContext


def run_rules(rules: List[PromptRule], normalized: NormalizedPrompt, ctx: RuleContext) -> List[Issue]:
    issues: List[Issue] = []
    for rule in rules:
        issues.extend(rule.evaluate(normalized, ctx))
    return issues