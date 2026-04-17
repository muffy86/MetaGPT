#!/usr/bin/env python3
from __future__ import annotations

import json


def run() -> dict:
    return {"a": 0.91, "b": 0.89, "winner": "a"}


if __name__ == "__main__":
    print(json.dumps(run()))
