from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from prompt_analysis.report import Issue


@dataclass(frozen=True)
class RuleContext:
    model: str
    tokenizer: str
    budgets: Dict[str, Any]


class PromptRule(Protocol):
    code: str
    def evaluate(self, normalized: "NormalizedPrompt", ctx: RuleContext) -> List[Issue]: ...


@dataclass(frozen=True)
class NormalizedPrompt:
    messages: List[Dict[str, str]]
    joined_text: str
    user_text: str
    system_text: str
    context_text: str