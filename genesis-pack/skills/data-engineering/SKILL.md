---
name: data-engineering
description: >-
  Data pipeline skill for Polars, DuckDB, Parquet, and contract checks.
  Triggers on "analyze this csv", "join these sources", and "build report".
when_to_use: >-
  Use for ingestion shaping, transformation pipelines, and reproducible data products.
---

# Data Engineering

1. Ingest to `exocortex.events` schema only.
2. Prefer Polars; use pandas only as interop shim.
3. Store durable outputs as Parquet.
4. Emit pipeline spans and deterministic run IDs.

DO NOT use for: ad-hoc local spreadsheet editing flows.

## Gotchas
- Schema drift silently breaks downstream retrieval ranking.
- Null handling must be explicit before embedding generation.
- Late-arriving data needs idempotent upsert keys.
