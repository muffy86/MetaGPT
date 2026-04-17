# Pack 02 — sensors

Universal ingestion fabric built on Redpanda Connect.

## Contract

- Every connector emits to a single Iceberg table: `events`
- Every event includes at minimum:
  - `id` (uuid v7)
  - `ts` (epoch seconds)
  - `source`
  - `kind`
  - `actor`
  - `subjects`
  - `title`
  - `body`
  - `meta`
- PII/secret handling happens in `transforms/redact.py` before write.

## Defaults

`scripts/enable-defaults.sh` enables:

- `screenpipe.yaml`
- `clipboard.yaml`
- `browser-history.yaml`
- `cli-history.yaml`
- `obsidian.yaml`

## Inputs shipped

1. `gmail.yaml`
2. `imessage.yaml`
3. `screenpipe.yaml`
4. `github.yaml`
5. `gcal.yaml`
6. `slack.yaml`
7. `discord.yaml`
8. `telegram.yaml`
9. `signal.yaml`
10. `sms.yaml`
11. `linear.yaml`
12. `obsidian.yaml`
13. `apple-notes.yaml`
14. `readwise.yaml`
15. `whisper.yaml`
16. `browser-history.yaml`
17. `health.yaml`
18. `finance.yaml`
19. `cli-history.yaml`
20. `clipboard.yaml`
21. `email-imap.yaml`

`inputs/` includes all files above; consumers can disable any source by removing
the file from runtime config or excluding it in deployment overlays.
