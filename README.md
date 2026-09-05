<div align="center">
  <img src="https://raw.githubusercontent.com/fport/strands-issue-writer/main/assets/logo.png" alt="strands-issue-writer" width="180">
  <h1>strands-issue-writer</h1>
  <p><strong>Turn product chatter into well-formed issues.</strong> Locally served, rule-checked, never invented.</p>
  <p>
    <a href="https://pypi.org/project/strands-issue-writer/"><img alt="PyPI" src="https://img.shields.io/pypi/v/strands-issue-writer?style=flat-square&color=F97316"></a>
    <a href="https://pypi.org/project/strands-issue-writer/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/strands-issue-writer?style=flat-square"></a>
    <a href="https://github.com/fport/strands-issue-writer/actions"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/fport/strands-issue-writer/ci.yml?style=flat-square&label=CI"></a>
    <a href="https://huggingface.co/datasets/fport/issue-writer-tr-en"><img alt="Dataset" src="https://img.shields.io/badge/%F0%9F%A4%97%20dataset-issue--writer--tr--en-yellow?style=flat-square"></a>
    <a href="https://github.com/fport/strands-issue-writer/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=flat-square"></a>
  </p>
</div>

---

A [Strands](https://strandsagents.com/) agent that turns raw product chatter —
Slack messages, support tickets, Sentry alerts, meeting notes — into well-formed
issue tracker entries, using a **fine-tuned model you serve yourself**.

Nothing leaves your machine. The model is the one trained in
[fport/issue-writer](https://github.com/fport/issue-writer) on
[fport/issue-writer-tr-en](https://huggingface.co/datasets/fport/issue-writer-tr-en),
served through Ollama or vLLM.

```
$ strands-issue-writer draft "selam, müşteriler fatura geçmişini tek tek açmak
yerine toplu PDF olarak indirmek istiyor. muhasebeciler ayda 30-40 fatura
indiriyor, çok vakit alıyor. bu sprint yetişir mi?"

[Story] Fatura geçmişini tek PDF olarak dışa aktarma ekle
priority Medium · 5 points
components: Billing  labels: export, self-service

h2. Kullanıcı Hikâyesi
Bir muhasebe işlerini yürüten müşteri olarak fatura geçmişimi tek bir PDF olarak
indirmek istiyorum; böylece her faturayı tek tek açmak zorunda kalmayayım.
...

Assumptions:
  - Dışa aktarma kapsamının seçilen tarih aralığı olduğu varsayıldı; girdide sınır
    belirtilmedi.
Open questions:
  - İndirilebilecek en geniş tarih aralığı ne olmalı?
```

## Two models, two jobs

The distinction matters and it is easy to get wrong:

**The writer** is the fine-tuned model behind `draft_issue`. It is good at exactly
one thing — turning messy input into a structured issue that obeys the writing
rules. It is not a general assistant and should not be asked to reason about your
backlog.

**The orchestrator** runs the Strands reasoning loop: which tool to call, whether a
draft is good enough, when to ask instead of guess. By default it is the same local
model, which keeps everything offline. Give it a stronger model when you want better
judgement about pushing back on a draft:

```python
from strands.models.anthropic import AnthropicModel
from strands_issue_writer import build_agent

agent = build_agent(orchestrator_model=AnthropicModel(model_id="claude-opus-5"))
```

The writer stays local either way — your product conversations never leave.

## Install

```bash
pip install "strands-issue-writer[ollama,dashboard]"     # or [vllm,dashboard]
```

From source, for development:

```bash
git clone https://github.com/fport/strands-issue-writer && cd strands-issue-writer
uv sync --group dev --extra ollama --extra dashboard
```

Then serve the model. [`docs/SERVING.md`](docs/SERVING.md) covers going from a
trained LoRA adapter to a running endpoint; the short version:

```bash
huggingface-cli download fport/issue-writer-gemma4-gguf --include "*q4_k_m.gguf" --local-dir ./model
ollama create issue-writer -f Modelfile.example
export ISSUE_WRITER_PROVIDER=ollama ISSUE_WRITER_MODEL=issue-writer
strands-issue-writer doctor
```

## Use

```bash
strands-issue-writer doctor                    # is the endpoint alive, right model?
strands-issue-writer draft "…" [--json]        # one issue, rendered or as JSON
strands-issue-writer agent                     # interactive agent with all tools
strands-issue-writer dashboard                 # web UI on :8765
```

As a library:

```python
from strands_issue_writer import build_agent

agent = build_agent()
agent("Read inbox.jsonl and draft issues for anything that looks like a bug. "
      "Show me each one, do not push anything.")
```

## Tools

| Tool | What it does |
|---|---|
| `draft_issue` | raw text → validated `Issue` via the local writer model |
| `review_issue` | rule checks: schema, sections, reproduction steps, invented facts, criteria observability |
| `render_issue` | human-readable rendering for review before anything is published |
| `push_to_tracker` | creates the issue — **dry run unless `confirm=True`** |
| `read_inbox` | reads pending raw inputs from a `.jsonl` or `---`-separated file |

`review_issue` is deliberately **not** model-based. These are checks a rule can
make, so a rule makes them: deterministically, on every draft, for free. It catches
the failure that matters most with a small local model — inventing a version number
or a metric that was never in the input.

`push_to_tracker` refuses to publish without explicit confirmation. Creating tickets
in someone's tracker is an outward action; it should not happen because a model
decided it was helpful.

## Dashboard

```bash
strands-issue-writer dashboard
```

Three panels answering the three questions you actually have while a local model
drafts for you:

- **left** — the raw input, and a history of what you have drafted this session
- **centre** — the issue as it came out: type, summary, chips for priority and
  components, the rendered body
- **right** — the rule review. Green when it passes, and when it does not, the
  violations by name. Below that, the model's own assumptions and open questions,
  which is where you find out whether it filled a gap honestly or silently.

The header shows which provider and model answered, and how long it took. A local
4B model on a laptop runs about 3–8 seconds per issue.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `ISSUE_WRITER_PROVIDER` | `ollama` | `ollama`, `vllm`, or `openai` |
| `ISSUE_WRITER_MODEL` | `issue-writer` | served model name |
| `ISSUE_WRITER_HOST` | `http://localhost:11434` | Ollama host |
| `ISSUE_WRITER_BASE_URL` | `http://localhost:8000/v1` | OpenAI-compatible endpoint |
| `ISSUE_WRITER_TEMPERATURE` | `0` | leave it there; the output is a schema |
| `TRACKER_URL` / `TRACKER_EMAIL` / `TRACKER_TOKEN` | — | only needed to actually publish |

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

The test suite runs without a model: the contract, the rule review and the tracker
payloads are all deterministic. Only `draft_issue` needs a served endpoint, and
`doctor` tells you whether you have one.

## License

MIT.
