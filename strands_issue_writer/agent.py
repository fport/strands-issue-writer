"""The orchestrating agent.

Two models are in play and they do different jobs:

  * the fine-tuned writer, served locally, sits behind `draft_issue` and only writes
  * the orchestrator decides which tool to call and whether the draft is good enough

Running both on the local model works and keeps everything offline; putting a
stronger model in the orchestrator seat gives better judgement about when to push
back on a draft. `build_agent(orchestrator_model=...)` covers both.
"""
from __future__ import annotations

from strands import Agent

from .prompts import ORCHESTRATOR
from .provider import build_model, describe, health
from .tools import draft_issue, push_to_tracker, read_inbox, render_issue, review_issue

TOOLS = [draft_issue, review_issue, render_issue, push_to_tracker, read_inbox]


def build_agent(orchestrator_model=None, system_prompt: str | None = None,
                callback_handler=...):
    """Build the orchestrator.

    Args:
        orchestrator_model: model for the reasoning loop. Defaults to the same
            locally served model as the writer, which keeps the whole thing offline.
        system_prompt: override the default orchestration instructions.
        callback_handler: pass None to silence streaming output.
    """
    kwargs = {}
    if callback_handler is not ...:
        kwargs["callback_handler"] = callback_handler
    return Agent(
        model=orchestrator_model or build_model(),
        tools=TOOLS,
        system_prompt=system_prompt or ORCHESTRATOR,
        **kwargs,
    )


def preflight() -> tuple[bool, str]:
    """Check the serving endpoint before the agent runs, so a dead endpoint
    reads as a clear message instead of a stack trace mid-conversation."""
    ok, detail = health()
    return ok, f"{describe()}\n{detail}"
