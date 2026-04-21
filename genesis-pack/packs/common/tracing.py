from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

try:
    from opentelemetry import trace
except Exception:  # pragma: no cover
    trace = None


@contextmanager
def tool_span(name: str, **attrs: Any) -> Iterator[None]:
    if trace is None:
        yield
        return
    tracer = trace.get_tracer("genesis-pack")
    with tracer.start_as_current_span(name) as span:
        for k, v in attrs.items():
            span.set_attribute(k, v if isinstance(v, (str, int, float, bool)) else str(v))
        yield
