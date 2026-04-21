#!/usr/bin/env bash
set -e
cat packs/*/docker-compose.fragment.yml 2>/dev/null | yq ea '. as $item ireduce ({}; . *+ $item)' > docker-compose.yml
for f in packs/*/justfile.fragment; do [[ -f $f ]] && cat "$f" >> justfile.tmp; done
cat justfile.head justfile.tmp 2>/dev/null > justfile && rm -f justfile.tmp
cat packs/*/policies.rego.fragment 2>/dev/null > assets/policies.rego
opa check assets/policies.rego
echo "fragments merged"
