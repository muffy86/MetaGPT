---
name: code-review
description: >-
  Repository code-review skill for bug, regression, and security risk analysis.
  Triggers on "review this PR", "audit this diff", and "risk scan this change".
when_to_use: >-
  Use before merge or release to produce severity-ranked findings with line references.
---

# Code Review

1. Prioritize correctness, regressions, security, and missing tests.
2. Run static analyzers and report only actionable failures.
3. Include file/line citations for each finding.
4. Add residual risk and test gaps when no defects are found.

DO NOT use for: style-only rewrites without behavior impact.

## Gotchas
- Superficial lint cleanups can hide behavioral regressions.
- Generated files should not be primary evidence for logic bugs.
- Missing migration steps are common in infra-touching diffs.
