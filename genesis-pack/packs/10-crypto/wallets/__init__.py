from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Wallet:
    chain: str
    address: str


def load_wallets() -> list[Wallet]:
    return [Wallet(chain="base", address="0x0000000000000000000000000000000000000000")]
