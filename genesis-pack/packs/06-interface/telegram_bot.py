from __future__ import annotations

def handle_message(text: str) -> dict:
    return {"reply": f"received: {text[:120]}"}
