"""A Strands agent that turns raw product chatter into well-formed issues,
powered by a locally served fine-tuned model."""

from .agent import build_agent, preflight
from .models import Issue
from .tools import draft_issue, push_to_tracker, read_inbox, render_issue, review_issue

__version__ = "0.1.0"
__all__ = [
    "Issue",
    "build_agent",
    "draft_issue",
    "preflight",
    "push_to_tracker",
    "read_inbox",
    "render_issue",
    "review_issue",
]
