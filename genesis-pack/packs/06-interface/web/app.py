#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import asyncio
import json

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse

from packs.retrieval.api import retrieve
from packs.twin.api import Twin

app = FastAPI(title="Genesis Pack UI")


HTML = """
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <title>Genesis Pack</title>
    <style>
      body { font-family: system-ui, sans-serif; margin: 0; background:#0b1020; color:#e5e7eb; }
      .wrap { max-width: 900px; margin: 0 auto; padding: 20px; }
      .card { background:#111827; border:1px solid #1f2937; border-radius: 12px; padding: 16px; margin-bottom: 14px; }
      input, textarea, button, select { width:100%; box-sizing:border-box; padding:10px; margin:8px 0; border-radius:8px; border:1px solid #374151; background:#0f172a; color:#e5e7eb; }
      button { cursor:pointer; background:#2563eb; border:none; }
      pre { white-space:pre-wrap; overflow-wrap:anywhere; background:#0f172a; padding:12px; border-radius:8px; }
      .row { display:grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      a { color:#93c5fd; }
    </style>
  </head>
  <body>
    <div class=\"wrap\"> 
      <h1>Genesis Pack</h1>
      <p>Simple user shell for ask, daily brief, and twin tools.</p>

      <div class=\"card\"> 
        <h3>Ask</h3>
        <form method=\"post\" action=\"/ask\">
          <input name=\"query\" placeholder=\"what's on tomorrow\" required />
          <button type=\"submit\">Ask</button>
        </form>
      </div>

      <div class=\"card\"> 
        <h3>Daily Brief</h3>
        <form method=\"post\" action=\"/daily-brief\">
          <button type=\"submit\">Generate Brief</button>
        </form>
      </div>

      <div class=\"card\">
        <h3>Twin Draft</h3>
        <form method=\"post\" action=\"/twin/draft\">
          <div class=\"row\">
            <input name=\"channel\" value=\"work-email\" required />
            <input name=\"recipient\" placeholder=\"recipient (optional)\" />
          </div>
          <textarea name=\"prompt\" rows=\"4\" placeholder=\"Draft a follow-up email about tomorrow's meeting\" required></textarea>
          <button type=\"submit\">Draft</button>
        </form>
      </div>

      <p><small>API docs: <a href=\"/docs\">/docs</a></small></p>
    </div>
  </body>
</html>
"""


def _render_json(payload: Any) -> HTMLResponse:
    html = f"""<!doctype html><html><body style='font-family:system-ui;background:#0b1020;color:#e5e7eb;padding:20px'>
    <a href='/' style='color:#93c5fd'>← Back</a>
    <pre style='background:#111827;border:1px solid #1f2937;padding:12px;border-radius:10px'>{json.dumps(payload, indent=2, default=str)}</pre>
    </body></html>"""
    return HTMLResponse(html)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(HTML)


@app.post("/ask")
async def ask(query: str = Form(...)) -> HTMLResponse:
    hits = await retrieve(query, k=8)
    payload = {
        "query": query,
        "count": len(hits),
        "results": [
            {
                "event_id": h.event_id,
                "source": h.source,
                "title": h.title,
                "snippet": h.snippet,
                "score": h.score,
                "citations": [h.event_id],
            }
            for h in hits
        ],
    }
    return _render_json(payload)


@app.post("/daily-brief")
async def daily_brief() -> HTMLResponse:
    today = datetime.now(tz=timezone.utc).date().isoformat()
    q = f"summary for today {today} upcoming tomorrow"
    hits = await retrieve(q, k=10)
    lines = [f"- [{h.source}] {h.title} ({h.event_id})" for h in hits]
    payload = {
        "date": today,
        "summary": "\n".join(lines) if lines else "No events yet.",
        "citations": [h.event_id for h in hits],
    }
    return _render_json(payload)


@app.post("/twin/draft")
async def twin_draft(channel: str = Form(...), prompt: str = Form(...), recipient: str = Form("")) -> HTMLResponse:
    twin = Twin()
    result = await twin.draft(channel=channel, prompt=prompt, recipient=recipient or None)
    return _render_json(result.__dict__)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True})

