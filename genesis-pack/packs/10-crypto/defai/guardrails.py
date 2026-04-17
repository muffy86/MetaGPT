#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext

getcontext().prec = 28


@dataclass(slots=True)
class GuardrailInput:
    usd_amount: Decimal
    cap: Decimal
    oracle_divergence: Decimal
    simulated: bool
    policy_allowed: bool
    twin_confidence: Decimal
    reversible: bool


def evaluate(inp: GuardrailInput) -> dict:
    checks = {
        "cap": inp.usd_amount <= inp.cap,
        "oracle_divergence": inp.oracle_divergence <= Decimal("0.02"),
        "simulate": inp.simulated,
        "policy": inp.policy_allowed,
        "twin_prior": inp.twin_confidence >= Decimal("0.60"),
        "hitl": inp.reversible or inp.usd_amount <= (inp.cap / Decimal("2")),
    }
    return {"pass": all(checks.values()), "checks": checks}
