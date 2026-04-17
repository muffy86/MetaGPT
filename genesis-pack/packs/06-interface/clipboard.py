from __future__ import annotations

def normalize(text: str) -> dict:
    return {"source": "clipboard", "kind": "clipboard", "body": text}
