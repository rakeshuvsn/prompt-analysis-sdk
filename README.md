# Prompt Analysis SDK

Analyze, score, and optimize LLM prompts to reduce token waste and improve cost efficiency.

**Prompt Analysis SDK** is an open-source toolkit that statically evaluates prompts *before* they are sent to an LLM.  
It helps engineers write **clearer, cheaper, and more effective prompts**.

🚀 **Live Demo:** https://rakeshuvsn.github.io/prompt-analysis-sdk/

---

## ✨ Features

- 🔍 **Prompt quality scoring** (clarity, completeness, structure, efficiency)
- 📉 **Token waste estimation**
- 💰 **Cost estimation & savings forecasting** (model-aware)
- 🧠 **Deterministic prompt improvement suggestions**
- ⚙️ **Configurable rules, models, tokenizers, and pricing**
- 🧪 **CLI with CI-friendly exit codes**
- 🌐 **Browser demo powered by Pyodide (no backend required)**

---

## Why Prompt Analysis?

Most prompt tools focus on *generation*.  
This SDK focuses on **analysis**:

> _“Is this prompt missing constraints?”_  
> _“How many tokens might be wasted?”_  
> _“How much could this cost at scale?”_

The goal is to catch issues **early**, before prompts hit production.

---

## Installation

### Local / Development
```bash
git clone https://github.com/rakeshuvsn/prompt-analysis-sdk
cd prompt-analysis-sdk
pip install -e .
```bash
--- 
## Quick Start (CLI)

Analyze a prompt directly:

promptlint analyze --text "Write a summary of this"

With model & config:

promptlint analyze \
  --text "Write a summary of this" \
  --model gpt-4o-mini

Machine-readable JSON output:

promptlint analyze --text "Write a summary of this" --json

Fail CI if high-severity issues exist:

promptlint analyze --text "Write a summary of this" --fail-on high
Example Output
Overall score: 64/100
Tokens: input=10, output_est=300, wasted_est=6
Cost (USD): current=0.0001815 optimized=0.000144 savings=20.66%


Issues:
- MISSING_OUTPUT_FORMAT
- NO_OUTPUT_LIMIT
Python SDK Usage
from prompt_analysis import PromptAnalyzer
from prompt_analysis.config import AnalyzerConfig


cfg = AnalyzerConfig.load("promptanalysis.yml")
analyzer = PromptAnalyzer(cfg)


report = analyzer.analyze(
    "Write a summary of this",
    model="gpt-4o-mini"
)


print(report.to_json())
Configuration

Configuration is defined in promptanalysis.yml.

defaults:
  model: gpt-4o-mini
  tokenizer: approx
  expected_output_tokens: 300
  max_input_tokens: 2500


models:
  - name: gpt-4o-mini
    pricing:
      input_per_1k: 0.00015
      output_per_1k: 0.00060


  - name: claude-3-5-sonnet
    pricing:
      input_per_1k: 0.003
      output_per_1k: 0.015

Architecture Overview
prompt_analysis/
├── analyzer.py        # Core analysis engine
├── rules/             # Prompt linting rules
├── tokenizers/        # Pluggable token estimators
├── report.py          # JSON-compatible report contract
├── config.py          # Model & pricing configuration
cli/
├── main.py            # promptlint CLI
demo/
├── index.html         # GitHub Pages demo
├── app.js             # Pyodide bridge
Demo (GitHub Pages)

The demo runs the real Python SDK in the browser using Pyodide.

No backend

No API keys

Fully deterministic

👉 https://rakeshuvsn.github.io/prompt-analysis-sdk/

CI / Automation

The repository includes GitHub Actions workflows for:

✅ Linting & tests

🚀 Auto-deploying the demo to GitHub Pages

📦 (Optional) Publishing to PyPI on version tags

Roadmap

 JSON Schema for report contract

 Redundancy & verbosity detection rules

 RAG context cost analysis

 Node.js / TypeScript SDK

 C# / Java SDKs

 Research paper submission

Research Context

This project supports research into:

Prompt efficiency measurement

Static prompt analysis

Token cost optimization

Deterministic prompt improvement

A research paper draft is in progress.

Contributing

Contributions are welcome!

Fork the repo

Create a feature branch

Add tests where applicable

Open a PR

License

MIT License © 2026
Built by Rakesh Uvsn

Acknowledgements

Pyodide

Open-source LLM tooling community