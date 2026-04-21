#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import duckdb
import ulid

from guardrails import GuardrailInput, evaluate


def append_event(source: str, kind: str, body: str, title: str, sensitivity: str = "internal") -> str:
    event_id = str(ulid.new())
    con = duckdb.connect("data/ledger.duckdb")
    con.execute(
        """
        INSERT OR REPLACE INTO exocortex.events
        (id, ts, source, kind, actor, subjects, title, body, body_hash, meta, sensitivity)
        VALUES (?, ?, ?, ?, 'self', '[]', ?, ?, sha256(?), '{}', ?)
        """,
        [event_id, datetime.now(tz=timezone.utc), source, kind, title, body, body, sensitivity],
    )
    con.close()
    return event_id


def run() -> dict:
    inp = GuardrailInput(
        usd_amount=Decimal("100"),
        cap=Decimal("1000"),
        oracle_divergence=Decimal("0.01"),
        simulated=True,
        policy_allowed=True,
        twin_confidence=Decimal("0.75"),
        reversible=True,
    )
    verdict = evaluate(inp)
    event_id = append_event(
        source="crypto",
        kind="attestation",
        body=json.dumps(verdict),
        title="defai strategy attestation",
        sensitivity="internal",
    )
    return {"verdict": verdict, "event_id": event_id}


if __name__ == "__main__":
    print(json.dumps(run()))
