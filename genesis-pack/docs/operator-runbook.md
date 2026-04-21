# Operator Runbook (Path B)

## Purpose
Operational checklist for maintaining, debugging, and validating Genesis Pack as an operator stack.

## Daily workflow
1. `just exo-stats`
2. `just eval-all`
3. `python3 packs/05-autopilot/replay.py runs/<session>/trace.jsonl`
4. `python3 packs/08-forge/skill_lint.py skills`

## Incident workflow
1. Capture failing command output.
2. Re-run with deterministic replay.
3. Check policy gate: `python3 packs/08-forge/scripts/policy_check.py '{...}'`
4. Verify model ingress via LiteLLM health.
5. Append outcome to `memory/lessons.md`.

## Release gates
- compile passes
- doctor report generated
- completion report generated
- skill lint passes
- replay path runs

## Mobile profile operations
- set `.profile` to `android-termux` or `android-linux-terminal`
- run `just doctor-mobile`
- ensure non-compose checks are green
