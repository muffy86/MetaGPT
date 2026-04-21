---
name: context-rot-guard
description: >-
  Context-rot control skill for compaction, summarization, and plan pinning.
  Triggers on "refocus", "compact", and "too much context".
when_to_use: >-
  Use when token budget, turn count, or artifact volume exceeds healthy operating bounds.
---

# Context Rot Guard

1. Compact active state to decision log + active plan.
2. Move large outputs to artifacts and reference by pointer.
3. Preserve current objective and unresolved questions.
4. Emit `skill.thrash` when repeated invocations indicate decomposition failure.

DO NOT use for: replacing source artifacts with irreversible summaries.

## Gotchas
- Over-compaction can drop critical constraints.
- Unbounded history replay reintroduces the original rot.
- Missing pointers make summaries unverifiable.
