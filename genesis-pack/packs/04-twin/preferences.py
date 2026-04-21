#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PreferenceChoice:
    option: str
    score: float


def prefer(options: list[str], for_task: str) -> list[PreferenceChoice]:
    del for_task
    return [PreferenceChoice(option=o, score=1.0 / (i + 1)) for i, o in enumerate(options)]
