# Pack 09 — policy-security

Policy-as-code and hermetic secret handling layer.

Includes:

- `assets/policies.rego` for OPA policy gates
- `scripts/policy_gate.py` for pre-tool authorization checks
- `scripts/resolve_secret.py` for `op://` runtime resolution via 1Password CLI
