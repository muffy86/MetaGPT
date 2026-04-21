from __future__ import annotations

def summarize(screen_text: str) -> dict:
    return {"summary": screen_text[:280], "confidence": 0.7}
