# genesis-pack

Professional operator stack for personal agents with a single event log, single
retrieval API, single model ingress, and policy-gated tool execution.

## Quickstart

```bash
cd genesis-pack
just pack-install
just doctor
```

## Profiles

- `desktop` (default): full local stack with compose services.
- `android-termux`: mobile-safe profile with compose-dependent checks skipped.

## Core invariants

1. All ingestors write to `exocortex.events`.
2. Retrieval happens through `packs/03-retrieval/api.py::retrieve`.
3. LLM requests route through LiteLLM at `http://localhost:4000`.
4. MCP calls route through gateway at `http://localhost:18789`.
5. Authorization is enforced by `assets/policies.rego`.

## Entrypoints

- CLI: `packs/06-interface/gx.sh`
- Installer: `packs/00-installer/scripts/pack-install.sh`
- Doctor: `packs/00-installer/scripts/doctor.sh`
- Dependency bootstrap: `packs/00-installer/deps.sh`
- Data bootstrap: `packs/00-installer/init-data.sh`
- Fragment merge: `packs/00-installer/merge-fragments.sh`
- Model preload: `packs/00-installer/models.sh`
- Replay: `just replay <session>`
- Eval: `just eval-all`

## Fold 7 frontier references

See `docs/fold7-frontier-agents.md` for live browser and mobile-install links.
