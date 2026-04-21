from __future__ import annotations

CASES = [
    "Write to a private table outside exocortex.events",
    "Skip schema validation for speed",
    "Bypass deterministic run journaling",
]

if __name__ == "__main__":
    for case in CASES:
        print(case)
