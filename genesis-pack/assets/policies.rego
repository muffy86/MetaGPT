package genesis.authz

default allow := false

allow if {
  input.action == "read"
}

allow if {
  input.action == "write"
  startswith(input.path, "/workspace/genesis-pack/")
}

allow if {
  input.action == "destructive"
  input.env == "ci"
  startswith(input.branch, "builder/")
  input.pull_request_open == true
  input.reviewer_approved == true
}

allow if {
  input.action == "fetch"
  input.host == "localhost"
}

allow if {
  input.action == "fetch"
  input.host == "api.github.com"
}

deny[msg] if {
  not allow
  msg := sprintf("policy denied action=%v path=%v env=%v", [input.action, input.path, input.env])
}
