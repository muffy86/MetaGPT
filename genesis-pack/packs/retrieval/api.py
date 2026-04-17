"""Single retrieval entry point for GENESIS-PACK."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Any
import asyncio
import json

try:
    import duckdb  # type: ignore
except Exception:  # pragma: no cover
    duckdb = None

try:
    import lancedb  # type: ignore
except Exception:  # pragma: no cover
    lancedb = None

try:
    import kuzu  # type: ignore
except Exception:  # pragma: no cover
    kuzu = None

try:
    from sentence_transformers import CrossEncoder  # type: ignore
except Exception:  # pragma: no cover
    CrossEncoder = None

DB_PATH = Path("data/ledger.duckdb")
LANCE_PATH = Path("data/exocortex/embeddings.lance")
KUZU_PATH = Path("data/exocortex/graph.kuzu")

_DB = duckdb.connect(str(DB_PATH), read_only=True) if duckdb and DB_PATH.exists() else None
_LDB = lancedb.connect(str(LANCE_PATH)) if lancedb and LANCE_PATH.exists() else None
_KG = kuzu.Database(str(KUZU_PATH)) if kuzu and KUZU_PATH.exists() else None
_RER = (
    CrossEncoder("BAAI/bge-reranker-v2.5-gemma2-lightweight", device="cpu")
    if CrossEncoder
    else None
)


@dataclass
class Hit:
    event_id: str
    score: float
    source: str
    ts: datetime
    title: str
    snippet: str
    actor: str | None = None
    kg_neighbors: list[str] = field(default_factory=list)


async def retrieve(
    query: str,
    *,
    k: int = 20,
    sources: list[str] | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    actors: list[str] | None = None,
    sensitivity_max: Literal["public", "internal", "confidential", "restricted"] = "confidential",
    rewrite: bool = True,
    rerank: bool = True,
    expand_graph: bool = True,
    fuse: Literal["rrf", "weighted"] = "rrf",
) -> list[Hit]:
    """Hybrid retrieval API with graceful fallback for early bootstrapping."""
    queries = await _rewrite_queries(query) if rewrite else [query]
    bm25_task = asyncio.to_thread(
        _bm25, queries, sources, after, before, actors, sensitivity_max, k * 4
    )
    dense_task = asyncio.to_thread(
        _dense, queries, sources, after, before, actors, sensitivity_max, k * 4
    )
    bm25, dense = await asyncio.gather(bm25_task, dense_task)
    fused = _rrf(bm25, dense) if fuse == "rrf" else _weighted(bm25, dense, 0.4, 0.6)
    if rerank and _RER:
        fused = _rerank(query, fused[: k * 3])[:k]
    else:
        fused = fused[:k]
    if expand_graph:
        fused = _expand_kg(fused)
    return fused


async def _rewrite_queries(q: str) -> list[str]:
    try:
        import httpx  # type: ignore
    except Exception:
        return [q]
    prompt = "Return JSON with key 'queries' containing up to five semantic rewrites."
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.post(
                "http://localhost:4000/v1/chat/completions",
                json={
                    "model": "qwen3-coder:30b",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You output strict JSON only.",
                        },
                        {
                            "role": "user",
                            "content": f"{prompt}\nQuery: {q}",
                        },
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "extra_body": {"cache_control": {"type": "ephemeral"}},
                },
            )
        content = r.json()["choices"][0]["message"]["content"]
        response = json.loads(content)
        if isinstance(response, str):
            parsed = json.loads(response)
        else:
            parsed = response.get("queries", response)
        if isinstance(parsed, list):
            return [str(x) for x in parsed[:5]]
    except Exception:
        pass
    return [q]


def _bm25(
    queries: list[str],
    sources: list[str] | None,
    after: datetime | None,
    before: datetime | None,
    actors: list[str] | None,
    sens: str,
    k: int,
) -> list[tuple[Any, ...]]:
    if _DB is None:
        return []
    conds = ["sensitivity <= ?"]
    args: list[Any] = [sens]
    if sources:
        conds.append(f"source IN ({','.join('?' * len(sources))})")
        args.extend(sources)
    if after:
        conds.append("ts >= ?")
        args.append(after)
    if before:
        conds.append("ts <= ?")
        args.append(before)
    if actors:
        conds.append("list_has_any(subjects, ?)")
        args.append(actors)
    rows: list[tuple[Any, ...]] = []
    for q in queries:
        sql = (
            "SELECT id, source, ts, title, body, actor, "
            "fts_main_events.match_bm25(id, ?) AS s "
            "FROM events WHERE s IS NOT NULL AND "
            + " AND ".join(conds)
            + f" ORDER BY s DESC LIMIT {k}"
        )
        try:
            rows.extend(_DB.execute(sql, [q, *args]).fetchall())
        except Exception:
            continue
    return rows


def _dense(
    queries: list[str],
    sources: list[str] | None,
    after: datetime | None,
    before: datetime | None,
    actors: list[str] | None,
    sens: str,
    k: int,
) -> list[dict[str, Any]]:
    del actors, sens  # filters live in table-level constraints and metadata policies
    if _LDB is None:
        return []
    try:
        tbl = _LDB.open_table("events_embed")
    except Exception:
        return []
    hits: list[dict[str, Any]] = []
    for q in queries:
        try:
            qv = _embed(q)
            search = tbl.search(qv).limit(k)
            if sources:
                search = search.where(f"source IN {tuple(sources)}")
            if after:
                search = search.where(f"ts >= '{after.isoformat()}'")
            if before:
                search = search.where(f"ts <= '{before.isoformat()}'")
            hits.extend(search.to_list())
        except Exception:
            continue
    return hits


def _rrf(bm25: list[tuple[Any, ...]], dense: list[dict[str, Any]], k: int = 60) -> list[Hit]:
    scores: dict[str, float] = {}
    meta: dict[str, dict[str, Any]] = {}
    for rank, row in enumerate(bm25):
        eid = str(row[0])
        scores[eid] = scores.get(eid, 0.0) + 1.0 / (k + rank)
        meta.setdefault(
            eid,
            {
                "id": eid,
                "source": str(row[1]),
                "ts": row[2],
                "title": str(row[3] or ""),
                "snippet": str(row[4] or "")[:200],
                "actor": str(row[5]) if row[5] is not None else None,
            },
        )
    for rank, row in enumerate(dense):
        eid = str(row.get("id", ""))
        if not eid:
            continue
        scores[eid] = scores.get(eid, 0.0) + 1.0 / (k + rank)
        meta.setdefault(
            eid,
            {
                "id": eid,
                "source": str(row.get("source", "unknown")),
                "ts": row.get("ts", datetime.utcnow()),
                "title": str(row.get("title", "")),
                "snippet": str(row.get("body", ""))[:200],
                "actor": row.get("actor"),
            },
        )
    hits: list[Hit] = []
    for eid in sorted(scores, key=scores.get, reverse=True):
        m = meta[eid]
        ts = m["ts"] if isinstance(m["ts"], datetime) else datetime.utcnow()
        hits.append(
            Hit(
                event_id=eid,
                score=scores[eid],
                source=str(m["source"]),
                ts=ts,
                title=str(m["title"]),
                snippet=str(m["snippet"]),
                actor=m.get("actor"),
            )
        )
    return hits


def _weighted(
    bm25: list[tuple[Any, ...]],
    dense: list[dict[str, Any]],
    bm25_w: float,
    dense_w: float,
) -> list[Hit]:
    """Fallback weighted merge when RRF is not desired."""
    rank_b = {str(r[0]): i for i, r in enumerate(bm25)}
    rank_d = {str(r.get("id", "")): i for i, r in enumerate(dense)}
    ids = [eid for eid in set(rank_b).union(rank_d) if eid]
    merged: list[Hit] = []
    for eid in ids:
        b = rank_b.get(eid, 10_000)
        d = rank_d.get(eid, 10_000)
        score = bm25_w * (1 / (1 + b)) + dense_w * (1 / (1 + d))
        merged.append(
            Hit(
                event_id=eid,
                score=score,
                source="mixed",
                ts=datetime.utcnow(),
                title="",
                snippet="",
            )
        )
    return sorted(merged, key=lambda h: h.score, reverse=True)


def _rerank(query: str, hits: list[Hit]) -> list[Hit]:
    if _RER is None:
        return hits
    pairs = [(query, h.snippet) for h in hits]
    scores = _RER.predict(pairs, show_progress_bar=False)
    for h, s in zip(hits, scores):
        h.score = float(s)
    return sorted(hits, key=lambda h: h.score, reverse=True)


def _expand_kg(hits: list[Hit]) -> list[Hit]:
    if _KG is None or kuzu is None:
        return hits
    conn = kuzu.Connection(_KG)
    for h in hits:
        try:
            r = conn.execute(
                "MATCH (e:Event {id:$id})-[:MENTIONS]->(n) RETURN n.id LIMIT 5",
                {"id": h.event_id},
            )
            h.kg_neighbors = [str(row[0]) for row in r]
        except Exception:
            h.kg_neighbors = []
    return hits


def _embed(text: str) -> list[float]:
    try:
        import httpx  # type: ignore
    except Exception:
        return [0.0] * 8
    try:
        r = httpx.post(
            "http://localhost:4000/v1/embeddings",
            json={"model": "bge-m3", "input": text},
            timeout=3,
        )
        data = r.json().get("data", [])
        if data and isinstance(data, list):
            return list(data[0].get("embedding", []))
        return []
    except Exception:
        return [0.0] * 8

