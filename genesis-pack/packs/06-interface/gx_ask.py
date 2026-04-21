#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys

from packs.retrieval.api import retrieve


async def main() -> int:
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("missing query")
        return 2
    hits = await retrieve(query, k=5)
    for h in hits:
        print(f"- [{h.source}] {h.title} ({h.event_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
