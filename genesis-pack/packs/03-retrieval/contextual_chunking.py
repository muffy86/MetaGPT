"""Contextual chunking for retrieval augmentation."""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

CONTEXT_PROMPT = """<document>{doc}</document>
Here is the chunk we want to situate within the whole document:
<chunk>{chunk}</chunk>
Please give a short succinct context (<=50 tokens) to situate this chunk
within the overall document for retrieval. Answer only with the context."""


async def contextualize(doc: str, chunk: str, model: str = "qwen3-coder:30b") -> str:
    if httpx is None:
        return chunk
    prompt = CONTEXT_PROMPT.format(doc=doc[:8000], chunk=chunk[:4000])
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "http://localhost:4000/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Return concise context only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "extra_body": {"cache_control": {"type": "ephemeral"}},
                },
            )
            res.raise_for_status()
            ctx = res.json()["choices"][0]["message"]["content"].strip()
            if not ctx:
                return chunk
            return f"{ctx}\n\n{chunk}"
    except Exception:
        return chunk


async def contextualize_many(document: str, chunks: list[str], concurrency: int = 4) -> list[str]:
    sem = asyncio.Semaphore(concurrency)

    async def _one(ch: str) -> str:
        async with sem:
            return await contextualize(document, ch)

    return await asyncio.gather(*[_one(ch) for ch in chunks])
