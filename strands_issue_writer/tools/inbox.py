"""Reading raw input from a file, so the agent can work through a backlog."""
from __future__ import annotations

import json
from pathlib import Path

from strands import tool


@tool
def read_inbox(path: str = "inbox.jsonl", limit: int = 10) -> list[dict]:
    """Read pending raw inputs waiting to be turned into issues.

    Accepts a .jsonl file with one object per line ({"id", "text", ...}) or a
    plain text file where entries are separated by a line containing only ---.

    Args:
        path: file to read.
        limit: how many entries to return.
    """
    p = Path(path)
    if not p.exists():
        return [{"error": f"{path} not found"}]

    text = p.read_text(encoding="utf-8")
    if p.suffix == ".jsonl":
        out = []
        for i, line in enumerate(text.splitlines()):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    out.append({"id": f"line{i}", "text": line})
        return out[:limit]

    chunks = [c.strip() for c in text.split("\n---\n") if c.strip()]
    return [{"id": f"e{i+1}", "text": c} for i, c in enumerate(chunks)][:limit]
