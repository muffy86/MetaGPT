"""Temporal knowledge graph builder (Graphiti-like pattern).

This module keeps a minimal Kuzu schema and incrementally links Event nodes
to Person/Org/Project/Topic entities extracted from event text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import json
import re

try:
    import kuzu  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    kuzu = None  # type: ignore


ENTITY_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")


@dataclass
class EventRecord:
    event_id: str
    title: str
    body: str
    ts_iso: str


def init_graph(db_path: str = "data/exocortex/graph.kuzu") -> None:
    if kuzu is None:
        return
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    conn.execute("CREATE NODE TABLE IF NOT EXISTS Event(id STRING, ts STRING, PRIMARY KEY(id))")
    conn.execute("CREATE NODE TABLE IF NOT EXISTS Topic(id STRING, PRIMARY KEY(id))")
    conn.execute("CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Event TO Topic)")


def extract_entities(text: str) -> list[str]:
    """
    Fast local heuristic. Swap with LLM extraction once model endpoints are available.
    """
    out: list[str] = []
    for m in ENTITY_RE.finditer(text):
        token = m.group(1).strip()
        if token.lower() in {"the", "and", "for", "with"}:
            continue
        out.append(token)
    dedup: list[str] = []
    seen: set[str] = set()
    for t in out:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            dedup.append(t)
    return dedup[:30]


def upsert_event(record: EventRecord, db_path: str = "data/exocortex/graph.kuzu") -> dict[str, object]:
    if kuzu is None:
        return {"ok": False, "reason": "kuzu-not-installed"}
    init_graph(db_path)
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    conn.execute(
        "MERGE (e:Event {id:$id, ts:$ts})",
        {"id": record.event_id, "ts": record.ts_iso},
    )
    entities = extract_entities(f"{record.title}\n{record.body}")
    for ent in entities:
        conn.execute("MERGE (t:Topic {id:$id})", {"id": ent})
        conn.execute(
            "MATCH (e:Event {id:$eid}), (t:Topic {id:$tid}) MERGE (e)-[:MENTIONS]->(t)",
            {"eid": record.event_id, "tid": ent},
        )
    return {"ok": True, "event_id": record.event_id, "topics": entities}


def process_jsonl(path: str) -> dict[str, object]:
    total = 0
    touched = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            obj = json.loads(line)
            rec = EventRecord(
                event_id=str(obj.get("id")),
                title=str(obj.get("title", "")),
                body=str(obj.get("body", "")),
                ts_iso=str(obj.get("ts")),
            )
            result = upsert_event(rec)
            if result.get("ok"):
                touched += 1
    return {"total": total, "graph_updates": touched}
