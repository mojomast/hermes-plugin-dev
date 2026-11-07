# Testing

## 1. Offline unit tests with a fake ctx (no Hermes needed)

See `templates/hello-hermes/tests/test_plugin.py`. Must-haves:

- `FakeCtx.register_tool` mirrors the real signature, so an extra kwarg
  (e.g. `output_schema`) fails in your tests rather than in production.
- Registered tool names == `plugin.yaml` `provides_tools`; hooks == `provides_hooks`.
- Strict YAML: duplicate keys fail; `version` is a string.
- Handler tests per `op`, including the error path (`ok: false` with `fix`).
- No network by default. Mark and skip live tests.

## 2. Mock host

When panes or live tools need a host you don't have (CI, laptop without Hermes):

- Fake ctx + in-memory session/pane state + a tiny HTTP stub for `plugin_api.py`
  routes if needed.
- Contract tests: tool op → state the pane would render.
- In the README, label results "mock host" vs "verified in Hermes vX.Y.Z" honestly.

## 3. Hermes's own checks

```bash
hermes plugins doctor [path|installed-id] [--ci]   # default target "."
hermes plugins validate <path> [--install-deps]
```

- `doctor` runs discovery, manifest parsing, import and `register(ctx)` against
  real runtime contracts and prints registration counts. `--ci` exits non-zero on error.
- `validate` is the catalog-admission gate: config schema, UPPER_SNAKE `requires_env`,
  oauth, loadable entrypoint, Python deps (`--install-deps` installs them), a capability
  probe running `register()` in isolation, declared tools/hooks/middleware vs actual,
  built-in tool collisions, security scan, no-core-override check.
- Neither is a sandbox: plugin code runs as you. Only run code you trust.

Run both **at the exact SHA you will pin** (fresh clone + `git checkout <sha>`).

## 4. Security scanner notes

The scanner (`tools/plugin_guard_context.py` and friends) pattern-matches source.
Known benign trigger: the superuser command word (su+do) in any string, e.g. a cosmetic
item name, raises `sudo_usage`. The env-dump and filesystem-format command words have
similar patterns. **The scan covers Markdown too**, so docs and bundled skills that merely
*mention* these words trip it (this repo's own skill did, and was reworded). Rephrase, or
explain the finding in the PR.

## 5. Schema budget check

`python scripts/measure_schemas.py` → "N tools, M o200k tokens". Track it in CI or
the changelog; refactors toward composable tools should show the drop.

## 6. Before every push

Secret-scan the tree (gitleaks, trufflehog, or a grep for `sk-`, `ghp_`, `AIza`,
private hostnames, emails). Never commit `.env`, tokens, or API keys captured from panes.
