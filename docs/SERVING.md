# Serving the fine-tuned model locally

The agent talks to a model you serve yourself. This page covers getting from a
trained LoRA adapter to a running endpoint, and how to check it actually works.

## 0. What you have after training

The notebook in [fport/issue-writer](https://github.com/fport/issue-writer) leaves
you with a LoRA adapter — a few hundred MB of deltas, not a whole model. Serving
runtimes want either merged weights or a GGUF file, so there is one conversion step
before anything can serve it.

```python
# in the training notebook, after trainer.train()

# 16-bit merged weights — for vLLM, TGI, transformers
model.push_to_hub_merged("fport/issue-writer-gemma4", tokenizer,
                         save_method="merged_16bit", token=HF_TOKEN)

# GGUF — for Ollama, llama.cpp, LM Studio
model.push_to_hub_gguf("fport/issue-writer-gemma4-gguf", tokenizer,
                       quantization_method=["q4_k_m"], token=HF_TOKEN)
```

`q4_k_m` is the usual starting point: roughly a quarter of the size at a quality
loss most people cannot spot. For a 4B model that is about 2.5 GB. If output quality
drops noticeably after quantisation, try `q5_k_m` or `q8_0` before blaming training.

---

## 1. Ollama — the short path

Best when you want it running on a laptop in a few minutes.

```bash
# pull the GGUF you pushed
huggingface-cli download fport/issue-writer-gemma4-gguf \
  --include "*q4_k_m.gguf" --local-dir ./model
```

Write a `Modelfile` next to it:

```dockerfile
FROM ./model/issue-writer-gemma4.q4_k_m.gguf

# Deterministic output: the model fills a fixed schema, so sampling only
# introduces malformed JSON.
PARAMETER temperature 0
PARAMETER top_p 1
PARAMETER num_ctx 4096
PARAMETER num_predict 2048

SYSTEM """You are a senior agile delivery assistant. You turn raw product input into well-formed issues. Reply with a single valid JSON object and nothing else."""
```

```bash
ollama create issue-writer -f Modelfile
ollama run issue-writer "Turn this into an issue: cart empties when a guest logs in"
```

Point the agent at it:

```bash
export ISSUE_WRITER_PROVIDER=ollama
export ISSUE_WRITER_MODEL=issue-writer
export ISSUE_WRITER_HOST=http://localhost:11434

strands-issue-writer doctor
```

---

## 2. vLLM — the throughput path

Best when several people or a CI job hit the model, or when you want the adapter
served without merging.

```bash
pip install vllm

vllm serve fport/issue-writer-gemma4 \
  --served-model-name issue-writer \
  --max-model-len 4096 \
  --port 8000
```

Serving the base model with the adapter applied at runtime, no merge needed:

```bash
vllm serve unsloth/gemma-4-E4B-it \
  --enable-lora \
  --lora-modules issue-writer=fport/issue-writer-gemma4-lora \
  --max-lora-rank 32 \
  --port 8000
```

`--max-lora-rank` has to be at least the `r` used in training (32 in the notebook),
otherwise the adapter is rejected at load time.

```bash
export ISSUE_WRITER_PROVIDER=vllm
export ISSUE_WRITER_MODEL=issue-writer
export ISSUE_WRITER_BASE_URL=http://localhost:8000/v1

strands-issue-writer doctor
```

---

## 3. Anything else OpenAI-compatible

LM Studio, llama.cpp's server, text-generation-inference, a hosted endpoint — all
work through the same provider:

```bash
export ISSUE_WRITER_PROVIDER=openai
export ISSUE_WRITER_BASE_URL=http://localhost:1234/v1
export ISSUE_WRITER_MODEL=issue-writer
export ISSUE_WRITER_API_KEY=whatever      # most local servers ignore it
```

---

## 4. Check it before trusting it

`doctor` verifies the endpoint is up **and** that your model name is actually
served — the most common failure is an endpoint answering happily with a different
model loaded.

```bash
strands-issue-writer doctor
```

Then a real draft, end to end:

```bash
strands-issue-writer draft "hey team, users keep asking to export their invoice
history as one PDF instead of opening each invoice. accountants download 30-40 a
month, it takes forever. can we fit this sprint?"
```

You should get a rendered issue and a rule review. If the review reports violations,
that is the tooling working, not failing — read them.

---

## 5. When output looks wrong

**Plain prose instead of JSON.** The system prompt is missing or different from the
one used in training. Ollama takes it from the `SYSTEM` block in the Modelfile;
vLLM takes it per-request, which this package sends for you.

**JSON that stops mid-object.** The generation limit is too low. Outputs here run to
~1,400 tokens at p95; set `num_predict` / `max_tokens` to at least 2048.

**Fields drifting from the schema.** Check temperature is 0. Then check you are
serving the fine-tuned model and not the base one — `doctor` prints which model
answered.

**Quality clearly below the notebook's test scores.** Quantisation is the first
suspect. Compare `q4_k_m` against `q8_0` on the same ten inputs before changing
anything about training.
