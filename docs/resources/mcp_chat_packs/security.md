## Security Baseline

- Never invent, scrape, or suggest bypassing authentication to obtain API keys.
- Require signed webhook requests whenever `inbound_signature_secret` is configured.
- Reject malformed JSON payloads and oversized user messages early.
- Treat tool/skill execution as privileged and only allow declared skills.
