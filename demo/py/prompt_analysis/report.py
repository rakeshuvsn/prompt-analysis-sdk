from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class Severity:
    low = "low"
    medium = "medium"
    high = "high"


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    fix: str
    savings_tokens_est: int = 0
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class Scores:
    overall: int
    clarity: int
    completeness: int
    structure: int
    efficiency: int


@dataclass
class TokenEstimates:
    input_tokens: int
    output_tokens_est: int
    wasted_tokens_est: int
    redundant_tokens_est: int = 0
    boilerplate_tokens_est: int = 0
    output_risk_tokens_est: int = 0


@dataclass
class CostEstimate:
    currency: str = "USD"
    current: float = 0.0
    optimized: float = 0.0
    savings: float = 0.0
    savings_pct: float = 0.0
    input_per_1k: Optional[float] = None
    output_per_1k: Optional[float] = None


@dataclass
class Suggestions:
    missing: List[str] = field(default_factory=list)
    rewritten_prompt: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class PromptReport:
    schema_version: str = "1.0"
    sdk_version: str = "0.1.0"
    model: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    scores: Scores = field(default_factory=lambda: Scores(0, 0, 0, 0, 0))
    token_estimates: TokenEstimates = field(default_factory=lambda: TokenEstimates(0, 0, 0))
    cost_estimate: Optional[CostEstimate] = None
    issues: List[Issue] = field(default_factory=list)
    suggestions: Suggestions = field(default_factory=Suggestions)
    budgets: Optional[Dict[str, Any]] = None
    flags: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)