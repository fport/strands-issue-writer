"""Model providers for the locally served writer model.

Three ways to serve the fine-tuned adapter, in rough order of how quickly you can
get going:

    ollama  — merged GGUF, one binary, good for a laptop
    vllm    — merged 16-bit weights, OpenAI-compatible, good for throughput
    openai  — any other OpenAI-compatible endpoint (LM Studio, llama.cpp server)

See docs/SERVING.md for the serving commands themselves.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    kind: str = os.getenv("ISSUE_WRITER_PROVIDER", "ollama")
    model_id: str = os.getenv("ISSUE_WRITER_MODEL", "issue-writer")
    host: str = os.getenv("ISSUE_WRITER_HOST", "http://localhost:11434")
    base_url: str = os.getenv("ISSUE_WRITER_BASE_URL", "http://localhost:8000/v1")
    api_key: str = os.getenv("ISSUE_WRITER_API_KEY", "not-needed")
    temperature: float = float(os.getenv("ISSUE_WRITER_TEMPERATURE", "0"))
    max_tokens: int = int(os.getenv("ISSUE_WRITER_MAX_TOKENS", "2048"))


def build_model(cfg: ProviderConfig | None = None):
    """Returns a Strands model bound to the locally served writer.

    Temperature defaults to 0: the model emits JSON against a fixed schema, and
    sampling buys nothing but malformed output.
    """
    cfg = cfg or ProviderConfig()

    if cfg.kind == "ollama":
        from strands.models.ollama import OllamaModel
        return OllamaModel(
            host=cfg.host,
            model_id=cfg.model_id,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    if cfg.kind in ("vllm", "openai"):
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"base_url": cfg.base_url, "api_key": cfg.api_key},
            model_id=cfg.model_id,
            params={"temperature": cfg.temperature, "max_tokens": cfg.max_tokens},
        )

    raise ValueError(
        f"unknown provider {cfg.kind!r}; expected one of: ollama, vllm, openai")


def describe(cfg: ProviderConfig | None = None) -> str:
    cfg = cfg or ProviderConfig()
    where = cfg.host if cfg.kind == "ollama" else cfg.base_url
    return f"{cfg.kind} · {cfg.model_id} · {where} · temperature {cfg.temperature}"


def health(cfg: ProviderConfig | None = None) -> tuple[bool, str]:
    """Checks the endpoint before the agent starts, so failures are legible."""
    import httpx
    cfg = cfg or ProviderConfig()
    url = f"{cfg.host}/api/tags" if cfg.kind == "ollama" else f"{cfg.base_url}/models"
    try:
        r = httpx.get(url, timeout=4)
        r.raise_for_status()
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

    body = r.json()
    names = ([m["name"] for m in body.get("models", [])] if cfg.kind == "ollama"
             else [m["id"] for m in body.get("data", [])])
    if cfg.model_id not in names and not any(cfg.model_id in n for n in names):
        return False, (f"endpoint is up but {cfg.model_id!r} is not served. "
                       f"available: {', '.join(names) or 'none'}")
    return True, f"{cfg.model_id} is being served"
