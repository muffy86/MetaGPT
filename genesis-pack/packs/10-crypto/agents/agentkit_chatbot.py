#!/usr/bin/env python3
from __future__ import annotations

import json


def reply(message: str) -> dict:
    return {"framework": "agentkit", "reply": message[:120]}


if __name__ == "__main__":
    print(json.dumps(reply("hello")))
