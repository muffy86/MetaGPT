#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json

from api import Twin


async def card(handle: str) -> dict:
    twin = Twin()
    return await twin.relationship(handle)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("handle")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(card(args.handle)), indent=2))
