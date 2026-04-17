"""Framework registry for decentralized agent execution surfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["s-tier", "a-tier", "experimental"]


@dataclass(slots=True, frozen=True)
class Framework:
    name: str
    language: str
    niche: str
    reason: str
    tier: Tier = "s-tier"


FRAMEWORKS: tuple[Framework, ...] = (
    Framework(
        name="elizaos-v2",
        language="typescript",
        niche="crypto-native multi-agent plugin runtime",
        reason="ecosystem gravity + plugin-goat compatibility",
    ),
    Framework(
        name="goat-sdk",
        language="typescript+python",
        niche="onchain tool abstraction",
        reason="200+ plugins and framework/wallet agnostic APIs",
    ),
    Framework(
        name="coinbase-agentkit-cdp",
        language="typescript+python",
        niche="enterprise wallet and action primitives",
        reason="production wallet rails for EVM and Solana",
    ),
    Framework(
        name="arc",
        language="rust",
        niche="solana low-latency DeFAI",
        reason="performance profile for tight execution loops",
    ),
    Framework(
        name="virtuals-game",
        language="typescript+python",
        niche="tokenized agents on Base",
        reason="agent-as-token primitives with integrated token economics",
    ),
    Framework(
        name="olas",
        language="python",
        niche="autonomous services with onchain verification",
        reason="service mesh pattern with Safe-backed control plane",
    ),
    Framework(
        name="zerepy",
        language="python",
        niche="python social and DeFi agents",
        reason="minimal ops profile and GOAT compatibility",
    ),
    Framework(
        name="mastra",
        language="typescript",
        niche="typed workflows and eval-centric orchestration",
        reason="high-DX typed workflows for non-crypto-heavy edges",
    ),
    Framework(
        name="near-shade-agents",
        language="python+rust",
        niche="tee-verified agent signatures",
        reason="MPC chain signatures from unified account context",
    ),
)


def by_language(language: str) -> list[Framework]:
    key = language.strip().lower()
    return [f for f in FRAMEWORKS if key in f.language]


def names() -> list[str]:
    return [f.name for f in FRAMEWORKS]
