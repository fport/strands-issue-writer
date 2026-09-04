"""The writer tool: raw text in, validated Issue out."""
from __future__ import annotations

import json

from pydantic import ValidationError
from strands import tool

from ..models import Issue
from ..prompts import WRITER
from ..provider import build_model

_writer = None


def _agent():
    """One writer agent, reused. It carries no tools: it only writes."""
    global _writer
    if _writer is None:
        from strands import Agent
        _writer = Agent(model=build_model(), tools=[], callback_handler=None)
    return _writer


def _detect_lang(text: str) -> str:
    """Cheap language guess. The writer was trained on both, but the system
    prompt has to be in the right one for the output to land in it."""
    tr_markers = "çğıöşüÇĞİÖŞÜ"
    tr_words = (" bir ", " için ", " ve ", " bu ", " ile ", " var ", " yok ")
    if any(c in text for c in tr_markers):
        return "tr"
    low = f" {text.lower()} "
    return "tr" if sum(w in low for w in tr_words) >= 2 else "en"


@tool
def draft_issue(raw_input: str, language: str = "auto") -> dict:
    """Turn raw product input into a structured issue.

    Use this for Slack messages, support tickets, meeting notes, Sentry alerts —
    anything unstructured that should become a tracker entry.

    Args:
        raw_input: the unstructured text as it arrived, quoted verbatim.
        language: "en", "tr", or "auto" to detect from the input.

    Returns:
        The issue as a dict, plus a `_meta` key carrying validation state. If the
        model produced something off-schema, `_meta.valid` is False and
        `_meta.error` explains what — do not pretend the draft succeeded.
    """
    lang = _detect_lang(raw_input) if language == "auto" else language
    prompt = (f"{'Bunu bir kayda çevir.' if lang == 'tr' else 'Turn this into an issue.'}"
              f"\n\n---\n{raw_input}\n---")

    agent = _agent()
    agent.system_prompt = WRITER.get(lang, WRITER["en"])

    try:
        issue = agent.structured_output(Issue, prompt)
        return {**issue.model_dump(), "_meta": {"valid": True, "language": lang}}
    except ValidationError as e:
        return {"_meta": {"valid": False, "language": lang,
                          "error": "output did not match the schema",
                          "detail": e.errors()[:3]}}
    except Exception as e:
        # Structured output can be unsupported by the endpoint; fall back to
        # asking for raw JSON and parsing it ourselves.
        text = str(agent(prompt))
        text = text[text.find("{"):text.rfind("}") + 1]
        try:
            issue = Issue.model_validate(json.loads(text))
            return {**issue.model_dump(),
                    "_meta": {"valid": True, "language": lang, "fallback": True}}
        except Exception:
            return {"_meta": {"valid": False, "language": lang,
                              "error": f"{type(e).__name__}: {e}",
                              "raw": text[:600]}}
