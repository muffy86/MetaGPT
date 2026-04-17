"""Unified twin API for style, decisions, and relationships."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

try:
    import duckdb  # type: ignore
except Exception:  # pragma: no cover
    duckdb = None

from packs.retrieval.api import Hit, retrieve


@dataclass(slots=True)
class TwinAnswer:
    answer: str
    confidence: float
    citations: list[str]
    rationale: str


async def _llm(system: str, prompt: str, *, model: str = "qwen3-coder:30b", format: str | None = None) -> str:
    try:
        import httpx  # type: ignore
    except Exception:
        return prompt

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system or "Respond helpfully."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "extra_body": {"cache_control": {"type": "ephemeral"}},
    }
    if format == "json":
        payload["response_format"] = {"type": "json_object"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post("http://localhost:4000/v1/chat/completions", json=payload)
            res.raise_for_status()
            return res.json()["choices"][0]["message"].get("content", prompt)
    except Exception:
        return prompt


async def _voice_match(text: str, profile: dict[str, Any]) -> float:
    score = 0.5
    phrases = profile.get("phrases", [])[:10]
    if phrases:
        matches = sum(1 for p in phrases if p.lower() in text.lower())
        score += min(0.4, 0.05 * matches)
    avg_len = profile.get("avg_sent_len")
    if isinstance(avg_len, (float, int)) and avg_len > 0:
        chunks = [c.strip() for c in text.split(".") if c.strip()]
        if chunks:
            observed = sum(len(c.split()) for c in chunks) / len(chunks)
            if abs(observed - float(avg_len)) <= 5:
                score += 0.1
    return max(0.0, min(score, 0.99))


class Twin:
    def __init__(self, root: str = "data"):
        root_path = Path(root)
        self.data_root = root_path
        self.db = duckdb.connect(str(root_path / "ledger.duckdb"), read_only=True) if duckdb else None
        self.style = self._load_json(root_path / "twin" / "style.json", default=self._default_style())
        self.prefs = self._load_json(root_path / "twin" / "preferences.json", default={})

    @staticmethod
    def _load_json(path: Path, *, default: Any) -> Any:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(default, indent=2), encoding="utf-8")
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _default_style() -> dict[str, Any]:
        return {
            "work-email": {
                "avg_sent_len": 16,
                "hedging_rate": 0.07,
                "phrases": ["shipping this", "next step", "confirming"],
                "tech_score": 8,
                "never_use": ["just circling back", "kindly do the needful"],
            },
            "personal-text": {
                "avg_sent_len": 10,
                "hedging_rate": 0.03,
                "phrases": ["on it", "sounds good", "works for me"],
                "tech_score": 3,
                "never_use": ["per my previous email"],
            },
            "commit": {
                "avg_sent_len": 8,
                "hedging_rate": 0.0,
                "phrases": ["add", "fix", "refactor", "wire"],
                "tech_score": 9,
                "never_use": ["hopefully", "maybe"],
            },
        }

    async def draft(
        self,
        *,
        channel: str,
        prompt: str,
        recipient: str | None = None,
        model: str = "qwen3-coder:30b",
    ) -> TwinAnswer:
        profile = self.style.get(channel) or self.style["work-email"]
        base_source = channel.split("-")[0]
        exemplars = await retrieve(prompt, sources=[base_source], actors=["self"], k=5, rerank=True)
        sys = (
            f"Write in this exact voice for {channel}. "
            f"Avg sentence length={profile['avg_sent_len']}, "
            f"hedging={profile['hedging_rate']}, "
            f"technicality={profile['tech_score']}/10, "
            f"avoid={profile['never_use']}.\n"
            + "\n".join(f"> {e.snippet}" for e in exemplars)
        )
        if recipient:
            prompt = f"Recipient: {recipient}\n{prompt}"
        answer = await _llm(sys, prompt, model=model)
        score = await _voice_match(answer, profile)
        return TwinAnswer(
            answer=answer,
            confidence=score,
            citations=[e.event_id for e in exemplars],
            rationale=f"drafted in {channel} voice with local exemplar grounding",
        )

    async def would_i(self, *, situation: str, options: Sequence[str]) -> TwinAnswer:
        analogues = await retrieve(situation, k=10, rerank=True, sources=["memory"], expand_graph=True)
        if len(analogues) < 3:
            return TwinAnswer(
                answer="insufficient analogues",
                confidence=0.3,
                citations=[],
                rationale="not enough comparable events",
            )
        options_text = "\n".join(f"- {o}" for o in options)
        context = "\n".join(f"- {a.title}: {self._chose_in(a)}" for a in analogues[:10])
        prompt = (
            "Given these historical decisions:\n"
            f"{context}\n\n"
            f"New situation: {situation}\n"
            f"Options:\n{options_text}\n"
            'Output strict JSON: {"choice": "...", "confidence": 0.0, "reasoning": "..."}'
        )
        raw = await _llm("", prompt, model="qwen3-coder:30b", format="json")
        try:
            data = json.loads(raw)
            choice = data.get("choice", str(options[0]) if options else "unknown")
            conf = float(data.get("confidence", 0.6))
            reasoning = data.get("reasoning", "historical analogue matching")
        except Exception:
            choice = str(options[0]) if options else "unknown"
            conf = 0.55
            reasoning = "fallback parse path"
        return TwinAnswer(
            answer=choice,
            confidence=max(0.0, min(conf, 1.0)),
            citations=[a.event_id for a in analogues[:10]],
            rationale=reasoning,
        )

    async def relationship(self, handle: str) -> dict[str, Any]:
        hits = await retrieve(handle, actors=[handle], k=50, after=datetime(2020, 1, 1, tzinfo=timezone.utc))
        if not hits:
            return {"status": "unknown", "handle": handle}
        last = max(hits, key=lambda h: h.ts)
        topics = self._top_topics(hits)
        open_items = self._open_commitments(hits)
        now = datetime.now(tz=timezone.utc)
        delta_days = int((now - last.ts.replace(tzinfo=timezone.utc) if last.ts.tzinfo is None else now - last.ts).days)
        return {
            "status": "known",
            "handle": handle,
            "last_contact_ts": last.ts.isoformat(),
            "days_since": delta_days,
            "warmth": round(self._warmth_score(hits), 3),
            "topics": topics[:8],
            "open_commitments": open_items[:10],
            "citations": [h.event_id for h in hits[:10]],
        }

    def _chose_in(self, hit: Hit) -> str:
        snippet = hit.snippet.lower()
        if "decided" in snippet or "choose" in snippet:
            return hit.snippet[:160]
        return "inferred from event context"

    def _warmth_score(self, hits: Sequence[Hit]) -> float:
        recency_weight = 0.0
        now = datetime.now(tz=timezone.utc)
        for h in hits[:30]:
            ts = h.ts.replace(tzinfo=timezone.utc) if h.ts.tzinfo is None else h.ts
            days = max((now - ts).days, 0)
            recency_weight += 1.0 / (1.0 + days)
        return min(1.0, recency_weight / 8.0)

    def _top_topics(self, hits: Sequence[Hit]) -> list[str]:
        counter: dict[str, int] = {}
        for h in hits:
            words = [w.strip(".,:;!?()[]{}").lower() for w in h.snippet.split()]
            for w in words:
                if len(w) < 5:
                    continue
                counter[w] = counter.get(w, 0) + 1
        return [k for k, _ in sorted(counter.items(), key=lambda kv: kv[1], reverse=True)]

    def _open_commitments(self, hits: Sequence[Hit]) -> list[str]:
        markers = ("will", "send", "share", "tomorrow", "next week", "follow up", "todo")
        out: list[str] = []
        for h in hits:
            low = h.snippet.lower()
            if any(m in low for m in markers):
                out.append(h.snippet[:180])
        return out

