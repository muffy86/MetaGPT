package genesis.policy

default allow = false

# Destructive operations are CI-gated and branch-scoped.
allow if {
  input.action == "destructive"
  input.env == "ci"
  startswith(input.branch, "cursor/")
  endswith(input.branch, "-bbba")
  input.pull_request_open == true
  input.reviewer_approved == true
}

# Read operations are always allowed.
allow if {
  input.action == "read"
}

# Writes are allowed only inside workspace roots.
allow if {
  input.action == "write"
  startswith(input.path, "/workspace/")
}

# Network egress allow-list.
allow if {
  input.action == "fetch"
  some host
  host := input.host
  host == "api.github.com"
}

allow if {
  input.action == "fetch"
  some host
  host := input.host
  host == "localhost"
}

deny[msg] if {
  not allow
  msg := sprintf("policy denied action=%v path=%v env=%v", [input.action, input.path, input.env])
}
