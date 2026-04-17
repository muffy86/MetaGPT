from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HitlDecision:
    approved: bool
    reason: str


def require_hitl(reversible: bool, usd_amount: float, cap: float) -> bool:
    return (not reversible) or usd_amount > cap / 2
