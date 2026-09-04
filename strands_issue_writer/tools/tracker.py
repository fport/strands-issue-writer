"""Rendering and pushing. Pushing is opt-in and loud about it."""
from __future__ import annotations

import os

from strands import tool

TYPE_MAP = {"Story": "Story", "Bug": "Bug", "Task": "Task", "Epic": "Epic",
            "Spike": "Task", "Sub-task": "Sub-task"}


@tool
def render_issue(issue: dict) -> str:
    """Render an issue as readable text for a human to review before anything is pushed."""
    p = {k: v for k, v in issue.items() if not k.startswith("_")}
    lines = [
        f"[{p.get('issue_type')}] {p.get('summary')}",
        f"priority {p.get('priority')}"
        + (f" · severity {p['severity']}" if p.get("severity") else "")
        + (f" · {p['story_points']} points" if p.get("story_points") else ""),
        f"components: {', '.join(p.get('components') or [])}"
        f"  labels: {', '.join(p.get('labels') or [])}",
        "",
        p.get("description", ""),
    ]
    if p.get("assumptions"):
        lines += ["", "Assumptions:"] + [f"  - {a}" for a in p["assumptions"]]
    if p.get("clarifying_questions"):
        lines += ["", "Open questions:"] + [f"  - {q}" for q in p["clarifying_questions"]]
    return "\n".join(lines)


def _to_adf(md: str) -> dict:
    """Minimal markdown to Atlassian Document Format."""
    content, i = [], 0
    lines = md.split("\n")
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
        elif ln.startswith("h2. "):
            content.append({"type": "heading", "attrs": {"level": 2},
                            "content": [{"type": "text", "text": ln[4:]}]})
            i += 1
        elif ln.startswith(("* ", "# ")):
            marker, items = ln[0], []
            while i < len(lines) and lines[i].startswith(marker + " "):
                items.append({"type": "listItem", "content": [
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": lines[i][2:]}]}]})
                i += 1
            content.append({"type": "bulletList" if marker == "*" else "orderedList",
                            "content": items})
        else:
            buf = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("h2. ", "* ", "# ")):
                buf.append(lines[i])
                i += 1
            content.append({"type": "paragraph",
                            "content": [{"type": "text", "text": " ".join(buf)}]})
    return {"version": 1, "type": "doc", "content": content}


@tool
def push_to_tracker(issue: dict, project_key: str, confirm: bool = False) -> dict:
    """Create the issue in the tracker. Requires explicit confirmation.

    Args:
        issue: the drafted issue.
        project_key: the target project, e.g. "FIN".
        confirm: must be True. Without it this returns the payload for review
                 and creates nothing.

    Returns:
        Either {"dry_run": True, "payload": ...} or the created issue key.
    """
    p = {k: v for k, v in issue.items() if not k.startswith("_")}
    payload = {"fields": {
        "project": {"key": project_key},
        "issuetype": {"name": TYPE_MAP.get(p["issue_type"], "Task")},
        "summary": p["summary"][:255],
        "description": _to_adf(p["description"]),
        "labels": p.get("labels", []),
        "priority": {"name": p["priority"]},
        "components": [{"name": c} for c in p.get("components", [])],
    }}

    if not confirm:
        return {"dry_run": True, "payload": payload,
                "note": "nothing was created; call again with confirm=True to publish"}

    base, email, token = (os.getenv("TRACKER_URL"), os.getenv("TRACKER_EMAIL"),
                          os.getenv("TRACKER_TOKEN"))
    if not all((base, email, token)):
        return {"error": "TRACKER_URL, TRACKER_EMAIL and TRACKER_TOKEN must be set",
                "payload": payload}

    import httpx
    r = httpx.post(f"{base}/rest/api/3/issue", json=payload,
                   auth=(email, token), timeout=30)
    if r.status_code >= 300:
        return {"error": f"{r.status_code}", "body": r.text[:400], "payload": payload}
    created = r.json()
    return {"created": created.get("key"), "url": f"{base}/browse/{created.get('key')}"}
