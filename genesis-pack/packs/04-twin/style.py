#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re

import duckdb


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z']+", text)]


def build_profile(channel: str, out_dir: Path) -> Path:
    con = duckdb.connect("data/ledger.duckdb", read_only=True)
    rows = con.execute(
        "SELECT body FROM exocortex.events WHERE source = ? AND actor = 'self' ORDER BY ts DESC LIMIT 1000",
        [channel],
    ).fetchall()
    con.close()
    docs = [r[0] or "" for r in rows]
    words = [w for d in docs for w in _tokens(d)]
    counts = Counter(words)
    punct = Counter(ch for d in docs for ch in d if ch in "!?.,;")
    sent_lens = [len(s.split()) for d in docs for s in re.split(r"[.!?]+", d) if s.strip()]
    profile = {
        "avg_sentence_len": sum(sent_lens) / len(sent_lens) if sent_lens else 0,
        "vocabulary_vector": [w for w, _ in counts.most_common(500)],
        "punctuation_profile": dict(punct),
        "emoji_rate": 0.0,
        "exclamation_rate": punct.get("!", 0) / max(1, sum(punct.values())),
        "hedging_rate": sum(1 for w in words if w in {"maybe", "perhaps", "might"}) / max(1, len(words)),
        "characteristic_phrases": [w for w, _ in counts.most_common(30)],
        "tech_score": 7,
        "never_use": ["kindly do the needful"],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"style_{channel}.json"
    out.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="gmail")
    args = parser.parse_args()
    print(build_profile(args.channel, Path("data/twin")))
