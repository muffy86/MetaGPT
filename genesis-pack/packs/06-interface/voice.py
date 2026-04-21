from __future__ import annotations

def transcribe(path: str) -> dict:
    return {"path": path, "text": "", "engine": "whisper.cpp"}
