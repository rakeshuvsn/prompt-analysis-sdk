let pyodideReady = false;
let pyodide = null;
let lastSuggestedPrompt = null;

const el = (id) => document.getElementById(id);

function setStatus(msg) {
  el("status").textContent = msg;
}

function renderIssues(issues) {
  const box = el("issues");
  box.innerHTML = "";
  if (!issues || issues.length === 0) {
    box.textContent = "None ✅";
    return;
  }

  for (const i of issues) {
    const div = document.createElement("div");
    div.className = "issue";
    const sev = (i.severity || "low").toLowerCase();

    div.innerHTML = `
      <div class="top">
        <div><strong>${i.code}</strong></div>
        <div class="badge ${sev}">${sev}</div>
      </div>
      <div class="small">${i.message}</div>
      <div class="small"><strong>Fix:</strong> ${i.fix}</div>
    `;
    box.appendChild(div);
  }
}

function renderReport(r) {
  el("scoreOverall").textContent = `${r.scores.overall}/100`;
  el("scoreEfficiency").textContent = `${r.scores.efficiency}/100`;

  el("inputTokens").textContent = r.token_estimates.input_tokens;
  el("wastedTokens").textContent = r.token_estimates.wasted_tokens_est;

  if (r.cost_estimate) {
    const ce = r.cost_estimate;
    el("costBox").textContent =
      `${ce.currency}\n` +
      `current:   ${ce.current}\n` +
      `optimized: ${ce.optimized}\n` +
      `savings:   ${ce.savings} (${ce.savings_pct}%)`;
  } else {
    el("costBox").textContent = "–";
  }

  renderIssues(r.issues);

  lastSuggestedPrompt = r.suggestions?.rewritten_prompt || null;
  el("suggestedPrompt").textContent = lastSuggestedPrompt || "–";
  el("copyBtn").disabled = !lastSuggestedPrompt;

  el("rawJson").textContent = JSON.stringify(r, null, 2);
}

async function initPyodide() {
  setStatus("Loading Pyodide…");
    pyodide = await loadPyodide();
  setStatus("Installing Python dependencies…");

  // Install dependencies needed by the SDK
  await pyodide.loadPackage("micropip");
  await pyodide.runPythonAsync(`
import micropip
await micropip.install(["pyyaml"])
`);
setStatus("Installing Python dependencies…");


// Install PyYAML (required by prompt_analysis.config)
await pyodide.loadPackage("micropip");
await pyodide.runPythonAsync(`
import micropip
await micropip.install(["pyyaml"])
`);

  // Make demo/py importable
  pyodide.FS.mkdirTree("/home/py");
  // fetch python package files list dynamically is hard on Pages,
  // so we rely on pre-copied `demo/py/prompt_analysis/` folder.
  // Pyodide can import from current URL using micropip is possible, but this is simpler.

  // Add current directory and /home/py to sys.path
  await pyodide.runPythonAsync(`
import sys
sys.path.append('.')
sys.path.append('/home/py')
`);

  // Load the local python package into /home/py by fetching files that exist under demo/py/.
  // We'll fetch a known list of files that are required for MVP.
  const files = [
    "prompt_analysis/__init__.py",
    "prompt_analysis/analyzer.py",
    "prompt_analysis/config.py",
    "prompt_analysis/normalized.py",
    "prompt_analysis/report.py",
    "prompt_analysis/rules/__init__.py",
    "prompt_analysis/rules/base.py",
    "prompt_analysis/rules/runner.py",
    "prompt_analysis/rules/core/__init__.py",
    "prompt_analysis/rules/core/missing_output_format.py",
    "prompt_analysis/rules/core/no_output_limit.py",
    "prompt_analysis/tokenizers/__init__.py",
    "prompt_analysis/tokenizers/base.py",
    "prompt_analysis/tokenizers/approx.py",
  ];

  for (const f of files) {
    const resp = await fetch(`./py/${f}`);
    if (!resp.ok) {
      throw new Error(`Failed to fetch ./py/${f} (HTTP ${resp.status})`);
    }
    const content = await resp.text();
    const fullPath = `/home/py/${f}`;
    const dir = fullPath.split("/").slice(0, -1).join("/");
    pyodide.FS.mkdirTree(dir);
    pyodide.FS.writeFile(fullPath, content);
  }

  // Warm import
  await pyodide.runPythonAsync(`
from prompt_analysis.config import AnalyzerConfig
from prompt_analysis import PromptAnalyzer
`);

  pyodideReady = true;
  setStatus("Ready ✅");
}

async function analyze() {
  if (!pyodideReady) return;

  const prompt = el("prompt").value || "";
  const model = el("model").value;
  const expectedOutput = parseInt(el("expectedOutput").value || "300", 10);
  const maxInput = parseInt(el("maxInput").value || "2500", 10);

  setStatus("Analyzing…");

  // Keep config inline for demo; you can later load promptanalysis.yml into demo too
  const cfgYaml = `
defaults:
  model: "gpt-4o-mini"
  tokenizer: "approx"
  expected_output_tokens: 300
  max_input_tokens: 2500

models:
  - name: "gpt-4o-mini"
    tokenizer: "approx"
    default_max_output_tokens: 300
    pricing:
      currency: "USD"
      input_per_1k: 0.00015
      output_per_1k: 0.00060

  - name: "claude-3-5-sonnet"
    tokenizer: "approx"
    default_max_output_tokens: 400
    pricing:
      currency: "USD"
      input_per_1k: 0.00300
      output_per_1k: 0.01500
`.trim();

  pyodide.globals.set("PROMPT_TEXT", prompt);
  pyodide.globals.set("MODEL_NAME", model);
  pyodide.globals.set("EXPECTED_OUT", expectedOutput);
  pyodide.globals.set("MAX_IN", maxInput);
  pyodide.globals.set("CFG_YAML", cfgYaml);

  const result = await pyodide.runPythonAsync(`
import yaml
from prompt_analysis.config import AnalyzerConfig, AnalyzerDefaults, ModelProfile, ModelPricing
from prompt_analysis import PromptAnalyzer

data = yaml.safe_load(CFG_YAML) or {}

# Build AnalyzerConfig without filesystem
d = data.get("defaults", {}) or {}
defaults = AnalyzerDefaults(
    model=str(d.get("model","default")),
    tokenizer=str(d.get("tokenizer","approx")),
    expected_output_tokens=int(d.get("expected_output_tokens",300)),
    max_input_tokens=int(d.get("max_input_tokens",2500)),
)

models = {}
for m in (data.get("models") or []):
    pr = m.get("pricing") or None
    pricing = None
    if pr:
        pricing = ModelPricing(
            input_per_1k=float(pr.get("input_per_1k",0.0)),
            output_per_1k=float(pr.get("output_per_1k",0.0)),
            currency=str(pr.get("currency","USD")),
        )
    mp = ModelProfile(
        name=str(m["name"]),
        context_window_tokens=int(m.get("context_window_tokens",0)),
        default_max_output_tokens=int(m.get("default_max_output_tokens",300)),
        tokenizer=str(m.get("tokenizer","approx")),
        pricing=pricing,
    )
    models[mp.name] = mp

cfg = AnalyzerConfig(defaults=defaults, models=models)
analyzer = PromptAnalyzer(cfg)
report = analyzer.analyze(
    PROMPT_TEXT,
    model=MODEL_NAME,
    expected_output_tokens=int(EXPECTED_OUT),
    max_input_tokens=int(MAX_IN),
)

report.to_json(indent=2)
`);

  const parsed = JSON.parse(result);
  renderReport(parsed);
  setStatus("Ready ✅");
}

el("analyzeBtn").addEventListener("click", analyze);
el("copyBtn").addEventListener("click", async () => {
  if (!lastSuggestedPrompt) return;
  await navigator.clipboard.writeText(lastSuggestedPrompt);
  setStatus("Copied suggested prompt ✅");
  setTimeout(() => setStatus("Ready ✅"), 1200);
});

initPyodide().catch((e) => {
  console.error(e);
  setStatus("Failed to load demo: " + e.message);
});