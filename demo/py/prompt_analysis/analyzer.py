# prompt_analysis/analyzer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from prompt_analysis.config import AnalyzerConfig
from prompt_analysis.normalized import normalize_messages
from prompt_analysis.report import (
    CostEstimate,
    Issue,
    PromptReport,
    Scores,
    Severity,
    Suggestions,
    TokenEstimates,
)
from prompt_analysis.rules import DEFAULT_RULES
from prompt_analysis.rules.base import RuleContext
from prompt_analysis.rules.runner import run_rules
from prompt_analysis.tokenizers import TOKENIZERS


@dataclass
class AnalyzerOptions:
    expected_output_tokens: int = 300
    max_input_tokens: int = 2500
    model: str = "default"
    tokenizer: str = "approx"


class PromptAnalyzer:
    """
    Analyzer entrypoint with configurable model profiles + pricing.

    - Uses AnalyzerConfig for defaults + model-specific tokenizer/pricing
    - Runs rules to produce Issues
    - Estimates tokens/waste
    - Computes cost estimate (current vs optimized) when pricing is configured
    """

    def __init__(self, config: Optional[AnalyzerConfig] = None):
        self.cfg = config or AnalyzerConfig()

    def analyze(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        expected_output_tokens: Optional[int] = None,
        max_input_tokens: Optional[int] = None,
        tokenizer: Optional[str] = None,
    ) -> PromptReport:
        model = model or self.cfg.defaults.model
        expected_output_tokens = self.cfg.resolve_expected_output_tokens(model, expected_output_tokens)
        max_input_tokens = self.cfg.resolve_max_input_tokens(max_input_tokens)
        tokenizer = self.cfg.resolve_tokenizer(model, tokenizer)

        messages = [{"role": "user", "content": prompt or ""}]
        return self.analyze_messages(
            messages,
            model=model,
            expected_output_tokens=expected_output_tokens,
            max_input_tokens=max_input_tokens,
            tokenizer=tokenizer,
        )

    def analyze_messages(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        expected_output_tokens: Optional[int] = None,
        max_input_tokens: Optional[int] = None,
        tokenizer: Optional[str] = None,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> PromptReport:
        model = model or self.cfg.defaults.model
        expected_output_tokens = self.cfg.resolve_expected_output_tokens(model, expected_output_tokens)
        max_input_tokens = self.cfg.resolve_max_input_tokens(max_input_tokens)
        tokenizer = self.cfg.resolve_tokenizer(model, tokenizer)

        tok = TOKENIZERS.get(tokenizer)
        if tok is None:
            raise ValueError(f"Unknown tokenizer '{tokenizer}'. Available: {list(TOKENIZERS.keys())}")

        normalized = normalize_messages(messages, context_chunks=context_chunks)

        # Token estimates
        input_tokens = tok.count_messages(normalized.messages) + tok.count_text(normalized.context_text)
        output_tokens_est = max(int(expected_output_tokens or 0), 0)

        # Run rules
        ctx = RuleContext(model=model, tokenizer=tokenizer, budgets={"max_input_tokens": max_input_tokens})
        issues: List[Issue] = run_rules(DEFAULT_RULES, normalized, ctx)

        # Missing checklist from issues
        missing: List[str] = []
        code_to_missing = {
            "MISSING_OUTPUT_FORMAT": "Output format (e.g., JSON schema / bullets / table)",
            "NO_OUTPUT_LIMIT": "Output length limit (max words/tokens/bullets)",
        }
        for iss in issues:
            item = code_to_missing.get(iss.code)
            if item and item not in missing:
                missing.append(item)

        # Waste estimation (MVP)
        output_risk = 0
        if any(i.code == "MISSING_OUTPUT_FORMAT" for i in issues):
            output_risk += 40
        if any(i.code == "NO_OUTPUT_LIMIT" for i in issues):
            output_risk += 30

        wasted_tokens_est = min(int(input_tokens * 0.20) + output_risk, int(input_tokens * 0.6))
        wasted_tokens_est = max(wasted_tokens_est, 0)

        # Scores (MVP)
        efficiency = max(0, 100 - int((wasted_tokens_est / max(input_tokens, 1)) * 120))
        completeness = 100 - (20 if missing else 0)
        structure = 85 if not any(i.code == "MISSING_OUTPUT_FORMAT" for i in issues) else 70
        clarity = 80
        overall = int(round((clarity + completeness + structure + efficiency) / 4))

        rewritten = self._rewrite_suggestion(normalized.user_text or normalized.joined_text, expected_output_tokens)

        # Cost estimate (if pricing configured)
        pricing = self.cfg.get_pricing(model)
        cost_estimate = None
        if pricing:
            current = (input_tokens / 1000.0) * pricing.input_per_1k + (output_tokens_est / 1000.0) * pricing.output_per_1k

            # Optimized estimate: apply input savings + reduce output when missing format/limit
            input_savings = sum(max(0, i.savings_tokens_est) for i in issues)
            optimized_input = max(input_tokens - input_savings, 0)

            needs_output_controls = any(i.code in ("MISSING_OUTPUT_FORMAT", "NO_OUTPUT_LIMIT") for i in issues)
            output_reduction_factor = 0.8 if needs_output_controls else 1.0
            optimized_output = max(int(output_tokens_est * output_reduction_factor), 0)

            optimized = (optimized_input / 1000.0) * pricing.input_per_1k + (optimized_output / 1000.0) * pricing.output_per_1k
            savings = max(current - optimized, 0.0)
            savings_pct = (savings / current * 100.0) if current > 0 else 0.0

            cost_estimate = CostEstimate(
                currency=pricing.currency,
                current=float(round(current, 8)),
                optimized=float(round(optimized, 8)),
                savings=float(round(savings, 8)),
                savings_pct=float(round(savings_pct, 2)),
                input_per_1k=pricing.input_per_1k,
                output_per_1k=pricing.output_per_1k,
            )

        return PromptReport(
            model=model,
            scores=Scores(
                overall=overall,
                clarity=clarity,
                completeness=completeness,
                structure=structure,
                efficiency=efficiency,
            ),
            token_estimates=TokenEstimates(
                input_tokens=input_tokens,
                output_tokens_est=output_tokens_est,
                wasted_tokens_est=wasted_tokens_est,
                output_risk_tokens_est=output_risk,
            ),
            cost_estimate=cost_estimate,
            issues=issues,
            suggestions=Suggestions(
                missing=missing,
                rewritten_prompt=rewritten,
                notes=[],
            ),
            budgets={"max_input_tokens": max_input_tokens},
            flags={"mvp": True},
        )

    def _rewrite_suggestion(self, user_text: str, expected_output_tokens: int) -> str:
        user_text = (user_text or "").strip() or "(No user prompt provided)"
        return (
            "Task:\n"
            f"{user_text}\n\n"
            "Constraints:\n"
            f"- Keep the response within ~{expected_output_tokens} tokens (or less).\n"
            "- Be concise and avoid repetition.\n"
            "- If information is missing, ask up to 2 clarifying questions.\n\n"
            "Output format:\n"
            "- Use bullet points OR JSON (choose one and stick to it).\n"
        ).strip()