#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json

from api import Twin
from calibrate import write_report


async def _run(args: argparse.Namespace) -> int:
    twin = Twin()
    if args.cmd == "calibrate":
        print(write_report())
        return 0
    if args.cmd == "draft":
        res = await twin.draft(channel=args.channel, prompt=args.prompt)
        print(json.dumps(res.__dict__, indent=2))
        return 0
    if args.cmd == "would_i":
        opts = args.options.split("||") if args.options else []
        res = await twin.would_i(situation=args.situation, options=opts)
        print(json.dumps(res.__dict__, indent=2))
        return 0
    if args.cmd == "relationship":
        res = await twin.relationship(args.handle)
        print(json.dumps(res, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="gx twin")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("calibrate")
    d = sub.add_parser("draft")
    d.add_argument("channel")
    d.add_argument("prompt")
    w = sub.add_parser("would_i")
    w.add_argument("situation")
    w.add_argument("--options", default="")
    r = sub.add_parser("relationship")
    r.add_argument("handle")
    raise SystemExit(asyncio.run(_run(parser.parse_args())))
