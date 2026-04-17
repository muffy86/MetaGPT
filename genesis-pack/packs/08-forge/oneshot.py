#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json


def run(task: str, text: str) -> dict:
    return {"task": task, "preview": text[:120], "status": "ok"}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("task", choices=["ocr", "transcribe", "unminify", "reverse-api"])
    p.add_argument("text", nargs="?", default="")
    args = p.parse_args()
    print(json.dumps(run(args.task, args.text)))
