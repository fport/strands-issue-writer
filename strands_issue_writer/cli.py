"""Command line entry point."""
from __future__ import annotations

import argparse
import json
import sys

from .agent import build_agent, preflight
from .provider import ProviderConfig, describe
from .tools.draft import draft_issue
from .tools.review import review_issue
from .tools.tracker import render_issue


def cmd_doctor(_args) -> int:
    ok, detail = preflight()
    print(detail)
    if not ok:
        print("\nThe endpoint is not ready. See docs/SERVING.md — in short:")
        cfg = ProviderConfig()
        if cfg.kind == "ollama":
            print("  ollama serve")
            print(f"  ollama create {cfg.model_id} -f Modelfile")
        else:
            print(f"  vllm serve <model> --served-model-name {cfg.model_id} --port 8000")
        return 1
    print("ready")
    return 0


def cmd_draft(args) -> int:
    raw = args.text or sys.stdin.read()
    issue = draft_issue(raw_input=raw, language=args.lang)
    meta = issue.get("_meta", {})
    if not meta.get("valid"):
        print("draft failed:", meta.get("error"), file=sys.stderr)
        if meta.get("raw"):
            print(meta["raw"], file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({k: v for k, v in issue.items() if k != "_meta"},
                         ensure_ascii=False, indent=2))
    else:
        print(render_issue(issue=issue))

    verdict = review_issue(issue=issue, raw_input=raw)
    if verdict["violations"]:
        print("\nviolations:", file=sys.stderr)
        for v in verdict["violations"]:
            print(f"  - {v}", file=sys.stderr)
        return 2
    for w in verdict["warnings"]:
        print(f"\nwarning: {w}", file=sys.stderr)
    return 0


def cmd_agent(args) -> int:
    ok, detail = preflight()
    if not ok:
        print(detail, file=sys.stderr)
        return 1
    agent = build_agent()
    if args.prompt:
        agent(args.prompt)
        return 0
    print(f"{describe()}\ntype a message, or Ctrl-D to leave\n")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line:
            agent(line)


def cmd_dashboard(args) -> int:
    from .dashboard.server import serve
    serve(host=args.host, port=args.port)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="strands-issue-writer",
        description="Turn raw product chatter into well-formed issues, "
                    "using a locally served fine-tuned model.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="check the serving endpoint")
    d.set_defaults(fn=cmd_doctor)

    p = sub.add_parser("draft", help="draft a single issue from text or stdin")
    p.add_argument("text", nargs="?")
    p.add_argument("--lang", default="auto", choices=["auto", "en", "tr"])
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_draft)

    a = sub.add_parser("agent", help="run the orchestrating agent")
    a.add_argument("prompt", nargs="?")
    a.set_defaults(fn=cmd_agent)

    w = sub.add_parser("dashboard", help="serve the web dashboard")
    w.add_argument("--host", default="127.0.0.1")
    w.add_argument("--port", type=int, default=8765)
    w.set_defaults(fn=cmd_dashboard)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
