"""GOAT SDK adapter contract."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GoatRequest:
    tool: str
    args: dict
    chain: str


@dataclass(slots=True)
class GoatResult:
    ok: bool
    tx_hash: str | None
    data: dict


def execute(req: GoatRequest) -> GoatResult:
    # Placeholder for @goat-sdk integration.
    return GoatResult(ok=True, tx_hash=None, data={"tool": req.tool, "chain": req.chain, "args": req.args})
