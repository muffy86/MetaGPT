---
name: web-automation
description: >-
  Browser automation skill using MCP gateway with accessibility-tree-first navigation.
  Triggers on "fill this form", "drive this checkout", and "authenticated scrape".
when_to_use: >-
  Use for multi-step web tasks that require navigation, extraction, and deterministic tool execution.
---

# Web Automation

1. Route all browser calls through MCP gateway `http://localhost:18789`.
2. Prefer a11y tree snapshots over screenshot mode.
3. Emit OTel span per tool step.
4. Persist final artifacts and citations.

DO NOT use for: desktop macro automation outside browser contexts.

## Gotchas
- Cookie banners can hide actionable controls; dismiss before extraction.
- Captcha or MFA checkpoints require external completion.
- Infinite scroll pages require bounded pagination to avoid context rot.
