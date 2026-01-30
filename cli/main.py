from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from prompt_analysis import PromptAnalyzer
from prompt_analysis.config import AnalyzerConfig

app = typer.Typer(add_completion=False, help="Prompt Analysis SDK CLI (promptlint)")


def _read_stdin() -> str:
    import sys

    return sys.stdin.read()


def _severity_rank(s: str) -> int:
    s = (s or "").lower()
    return {"low": 1, "medium": 2, "high": 3}.get(s, 0)


@app.command("analyze")
def analyze(
    file: Optional[Path] = typer.Argument(
        None,
        help="Prompt file to analyze. If omitted, use --stdin or pass text with --text.",
    ),
    text: Optional[str] = typer.Option(None, "--text", help="Prompt text to analyze."),
    stdin: bool = typer.Option(False, "--stdin", help="Read prompt from STDIN."),
    config: str = typer.Option("promptanalysis.yml", "--config", help="Path to YAML config."),
    model: Optional[str] = typer.Option(
        None, "--model", help="Model name (overrides config default)."
    ),
    tokenizer: Optional[str] = typer.Option(None, "--tokenizer", help="Tokenizer name override."),
    expected_output_tokens: Optional[int] = typer.Option(
        None, "--expected-output", help="Expected output tokens (override)."
    ),
    max_input_tokens: Optional[int] = typer.Option(
        None, "--max-input", help="Max input token budget (override)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable JSON output."),
    fail_on: Optional[str] = typer.Option(
        None,
        "--fail-on",
        help="Exit non-zero if any issue meets/exceeds this severity: low|medium|high",
    ),
    min_score: Optional[int] = typer.Option(
        None,
        "--min-score",
        help="Exit non-zero if overall score is below this value (0-100).",
    ),
) -> None:
    """
    Analyze a prompt and print a report.
    """
    cfg_path = Path(config)
    cfg = AnalyzerConfig.load(cfg_path) if cfg_path.exists() else AnalyzerConfig()

    analyzer = PromptAnalyzer(cfg)

    if stdin:
        prompt_text = _read_stdin()
    elif text is not None:
        prompt_text = text
    elif file is not None:
        prompt_text = file.read_text(encoding="utf-8")
    else:
        raise typer.BadParameter("Provide a file OR --text OR --stdin")

    report = analyzer.analyze(
        prompt_text,
        model=model,
        tokenizer=tokenizer,
        expected_output_tokens=expected_output_tokens,
        max_input_tokens=max_input_tokens,
    )

    exit_code = 0

    if min_score is not None and report.scores.overall < int(min_score):
        exit_code = 2

    if fail_on:
        threshold = _severity_rank(fail_on)
        severities = []
        for i in report.issues:
            sev = i.severity.value if hasattr(i.severity, "value") else str(i.severity)
            severities.append(_severity_rank(sev))
        max_found = max(severities, default=0)
        if max_found >= threshold:
            exit_code = 2

    if json_out:
        typer.echo(report.to_json(indent=2))
        raise typer.Exit(code=exit_code)

    typer.echo(f"Model: {report.model}")
    typer.echo(f"Overall score: {report.scores.overall}/100")
    typer.echo(
        "Scores: "
        f"clarity={report.scores.clarity}, "
        f"completeness={report.scores.completeness}, "
        f"structure={report.scores.structure}, "
        f"efficiency={report.scores.efficiency}"
    )
    typer.echo(
        "Tokens: "
        f"input={report.token_estimates.input_tokens}, "
        f"output_est={report.token_estimates.output_tokens_est}, "
        f"wasted_est={report.token_estimates.wasted_tokens_est}"
    )

    if report.cost_estimate:
        ce = report.cost_estimate
        typer.echo(
            f"Cost ({ce.currency}): current={ce.current} optimized={ce.optimized} "
            f"savings={ce.savings} ({ce.savings_pct}%)"
        )

    if report.issues:
        typer.echo("\nIssues:")
        for i in report.issues:
            sev = i.severity.value if hasattr(i.severity, "value") else str(i.severity)
            typer.echo(f"- [{sev}] {i.code}: {i.message}")
            typer.echo(f"  Fix: {i.fix}")
    else:
        typer.echo("\nIssues: none ✅")

    if report.suggestions.rewritten_prompt:
        typer.echo("\nSuggested prompt:")
        typer.echo(report.suggestions.rewritten_prompt)

    raise typer.Exit(code=exit_code)