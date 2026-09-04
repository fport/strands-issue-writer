"""Dashboard server.

The point of the dashboard is not to look busy. It answers three questions a
person actually has while a local model drafts issues for them:

  1. is the endpoint alive and which model is answering
  2. what did the model produce, field by field
  3. which rules did it break, and did it invent anything

Everything streams over one websocket so the panels stay in step.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

HERE = Path(__file__).parent


def build_app():
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse

    from ..provider import describe, health
    from ..tools.draft import draft_issue
    from ..tools.review import review_issue

    app = FastAPI(title="issue writer")

    @app.get("/")
    async def index() -> HTMLResponse:
        return HTMLResponse((HERE / "index.html").read_text(encoding="utf-8"))

    @app.get("/api/status")
    async def status() -> dict:
        ok, detail = await asyncio.to_thread(health)
        return {"ok": ok, "detail": detail, "provider": describe()}

    @app.websocket("/ws")
    async def ws(sock: WebSocket) -> None:
        await sock.accept()
        ok, detail = await asyncio.to_thread(health)
        await sock.send_json({"type": "status", "ok": ok, "detail": detail,
                              "provider": describe()})
        try:
            while True:
                msg = json.loads(await sock.receive_text())
                raw = (msg.get("text") or "").strip()
                if not raw:
                    continue

                await sock.send_json({"type": "drafting", "input": raw})
                t0 = time.perf_counter()
                issue = await asyncio.to_thread(
                    draft_issue, raw_input=raw, language=msg.get("lang", "auto"))
                elapsed = time.perf_counter() - t0

                meta = issue.get("_meta", {})
                if not meta.get("valid"):
                    await sock.send_json({"type": "error", "meta": meta,
                                          "elapsed": round(elapsed, 2)})
                    continue

                verdict = await asyncio.to_thread(
                    review_issue, issue=issue, raw_input=raw)
                await sock.send_json({
                    "type": "issue",
                    "issue": {k: v for k, v in issue.items() if k != "_meta"},
                    "review": verdict,
                    "language": meta.get("language"),
                    "elapsed": round(elapsed, 2),
                })
        except WebSocketDisconnect:
            pass

    return app


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    try:
        import uvicorn
    except ImportError as e:
        raise SystemExit(
            "the dashboard needs its extras:  pip install 'strands-issue-writer[dashboard]'"
        ) from e
    print(f"dashboard on http://{host}:{port}")
    uvicorn.run(build_app(), host=host, port=port, log_level="warning")
