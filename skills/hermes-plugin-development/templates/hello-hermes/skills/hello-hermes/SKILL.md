---
name: hello-hermes
description: How to use the hello_hermes tool from the hello-hermes plugin.
---
# hello-hermes

- `hello_hermes` with `op: "status"` checks the plugin is loaded.
- `hello_hermes` with `op: "greet", name: "..."` returns a greeting.
- On `ok: false`, read `fix` and retry once with corrected arguments.
