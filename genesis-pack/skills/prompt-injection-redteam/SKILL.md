---
name: prompt-injection-redteam
description: >-
  Injection resilience testing skill for skills and tool workflows.
  Triggers on "redteam this skill", "injection test", and "pre-release hardening".
when_to_use: >-
  Use before publishing or enabling skills to validate refusal and policy adherence.
---

# Prompt Injection Redteam

1. Run corpus of embedded directives, tool confusion, and exfil payloads.
2. Verify policy gating remains authoritative under adversarial prompts.
3. Report pass-rate and weakest failure class.
4. Block release below threshold.

DO NOT use for: production user interactions that are not evaluations.

## Gotchas
- Encoded payloads bypass naive pattern matching.
- Tool-schema confusion often appears as valid-looking JSON.
- Weak models may comply under urgency framing.
