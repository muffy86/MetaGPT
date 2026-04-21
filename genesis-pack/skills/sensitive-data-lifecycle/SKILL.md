---
name: sensitive-data-lifecycle
description: >-
  Sensitive data lifecycle skill for ingest, tokenization, processing, and purge.
  Triggers on "contains PII", "redact this", and "process health records".
when_to_use: >-
  Use when data includes PII/PHI/financial identifiers or secret-like artifacts.
---

# Sensitive Data Lifecycle

1. Redact before model exposure.
2. Store redaction map under `runs/<session>/` with mode `0600`.
3. Process tokenized values only.
4. Rehydrate only for authorized final artifact generation.

DO NOT use for: plaintext secret extraction or logging.

## Gotchas
- Partial tokenization can leak enough context for re-identification.
- Logs often become accidental secondary data stores.
- Rehydration must be scoped to explicit output channels only.
