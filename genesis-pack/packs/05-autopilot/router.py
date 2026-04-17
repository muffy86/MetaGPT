"""Confidence-routed escalation and deterministic replay contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["T0", "T1", "T2", "T3"]


@dataclass(slots=True)
class RouteDecision:
    confidence: float
    tier: Tier
    mode: Literal["execute", "dual-run", "promote-turn"]
    reason: str


def route(confidence: float) -> RouteDecision:
    c = max(0.0, min(confidence, 1.0))
    if c >= 0.85:
        return RouteDecision(c, "T0", "execute", "high confidence")
    if c >= 0.60:
        return RouteDecision(c, "T1", "dual-run", "mid confidence, dual-run decision step")
    return RouteDecision(c, "T2", "promote-turn", "low confidence, promote full turn")


def next_tier(current: Tier) -> Tier:
    order: list[Tier] = ["T0", "T1", "T2", "T3"]
    idx = order.index(current)
    return order[min(idx + 1, len(order) - 1)]
