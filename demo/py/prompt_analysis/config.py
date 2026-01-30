from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml


@dataclass(frozen=True)
class ModelPricing:
    input_per_1k: float
    output_per_1k: float
    currency: str = "USD"


@dataclass(frozen=True)
class ModelProfile:
    name: str
    context_window_tokens: int = 0
    default_max_output_tokens: int = 300
    tokenizer: str = "approx"
    pricing: Optional[ModelPricing] = None


@dataclass
class AnalyzerDefaults:
    model: str = "default"
    tokenizer: str = "approx"
    expected_output_tokens: int = 300
    max_input_tokens: int = 2500


@dataclass
class AnalyzerConfig:
    defaults: AnalyzerDefaults = field(default_factory=AnalyzerDefaults)
    models: Dict[str, ModelProfile] = field(default_factory=dict)

    @staticmethod
    def load(path: str | Path) -> "AnalyzerConfig":
        p = Path(path)
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

        d = data.get("defaults", {}) or {}
        defaults = AnalyzerDefaults(
            model=str(d.get("model", "default")),
            tokenizer=str(d.get("tokenizer", "approx")),
            expected_output_tokens=int(d.get("expected_output_tokens", 300)),
            max_input_tokens=int(d.get("max_input_tokens", 2500)),
        )

        models: Dict[str, ModelProfile] = {}
        for m in (data.get("models") or []):
            name = str(m["name"])
            pricing = None
            pr = m.get("pricing") or None
            if pr:
                pricing = ModelPricing(
                    input_per_1k=float(pr.get("input_per_1k", 0.0)),
                    output_per_1k=float(pr.get("output_per_1k", 0.0)),
                    currency=str(pr.get("currency", "USD")),
                )

            models[name] = ModelProfile(
                name=name,
                context_window_tokens=int(m.get("context_window_tokens", 0)),
                default_max_output_tokens=int(m.get("default_max_output_tokens", defaults.expected_output_tokens)),
                tokenizer=str(m.get("tokenizer", defaults.tokenizer)),
                pricing=pricing,
            )

        if "default" not in models:
            models["default"] = ModelProfile(
                name="default",
                context_window_tokens=0,
                default_max_output_tokens=defaults.expected_output_tokens,
                tokenizer=defaults.tokenizer,
                pricing=None,
            )

        return AnalyzerConfig(defaults=defaults, models=models)

    def get_model(self, model: Optional[str]) -> ModelProfile:
        name = model or self.defaults.model
        return self.models.get(name) or self.models["default"]

    def get_pricing(self, model: Optional[str]) -> Optional[ModelPricing]:
        return self.get_model(model).pricing

    def resolve_tokenizer(self, model: Optional[str], tokenizer_override: Optional[str]) -> str:
        if tokenizer_override:
            return tokenizer_override
        mp = self.get_model(model)
        return mp.tokenizer or self.defaults.tokenizer

    def resolve_expected_output_tokens(self, model: Optional[str], expected_override: Optional[int]) -> int:
        if expected_override is not None:
            return int(expected_override)
        mp = self.get_model(model)
        return int(mp.default_max_output_tokens or self.defaults.expected_output_tokens)

    def resolve_max_input_tokens(self, max_override: Optional[int]) -> int:
        if max_override is not None:
            return int(max_override)
        return int(self.defaults.max_input_tokens)