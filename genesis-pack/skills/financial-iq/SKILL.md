---
name: financial-iq
description: >-
  Finance analysis skill over redacted events in DuckDB using Decimal math.
  Triggers on "cashflow", "runway", and "allocation drift".
when_to_use: >-
  Use for financial summaries, anomaly detection, and projection outputs with citations.
---

# Financial IQ

1. Read only from `exocortex.events` via `retrieve()`.
2. Use `decimal.Decimal` with fixed precision for calculations.
3. Emit citations for every recommendation.
4. Redact sensitive outputs unless explicitly authorized by policy.

DO NOT use for: brokerage API trading execution.

## Gotchas
- Float math introduces drift in rolling balances.
- Category merges can hide anomalies if done pre-normalization.
- FX rates must include retrieval timestamp to remain auditable.
