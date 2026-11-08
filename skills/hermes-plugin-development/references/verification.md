# Verification log

Checked on 2026-11-07 against a NousResearch/hermes-agent checkout at commit
`9a6f834757` (main, 2026-11-06) and an installed `hermes` CLI reporting
**Hermes Agent v0.23.0**.

## Verified against source / by running

| Claim | Where |
|---|---|
| `register_tool` signature; no `output_schema`; `override` needs `allow_tool_override` | `hermes_cli/plugins_context.py` |
| `register_hook(hook_name, callback, *, hold_stream=False)`, `call_mcp`, `register_command`, other ctx methods listed | `hermes_cli/plugins_context.py` |
| `register_skill(name, path, description, frontmatter)` → `<plugin>:<name>`, not copied | `hermes_cli/plugins_content.py` |
| `plugin_data_dir` / `plugin_db` (profile-aware, WAL) | `plugins/plugin_storage.py` |
| `agent.secret_scope.get_secret`; credential rule 11 | `agent/secret_scope.py`, `plugin-catalog/README.md` |
| Catalog entry schema, image hosts, ≤6 screenshots, tiers, categories, rules 1–18 | `plugin-catalog/README.md` |
| `scripts/validate_plugin_catalog.py [--json] paths`; unquoted sha error text | ran it |
| `hermes plugins doctor [target] [--ci]`, `hermes plugins validate path [--install-deps]` | `hermes_cli/subcommands/plugins.py`; ran both |
| Already-mounted `/api/plugins/<name>/` routes not re-mounted | `hermes_cli/web_server_dashboard.py` (`_plugin_api_mounted`) |
| Rescan endpoint, manifest.json fields (`tab.path`, `position`, `slots`, `css`, `api`) | `extending-the-dashboard.md` |
| Desktop imports limited to `@hermes/plugin-sdk` and `react` | `desktop-plugin-sdk.md` |
| `plugins.isolation: host` | `website/docs/user-guide/features/plugins.md`; validate output |
| `sudo_usage` pattern + inert-literal handling | `tools/plugin_guard_context.py` |
| `pre_llm_call` / `on_session_start` hooks | `developer-guide/plugins/index.md` |
| Template plugin: pytest 3/3, `hermes plugins validate` "Validation passed", `doctor --ci` OK (1 tool) | ran |
| Template catalog entry passes `validate_plugin_catalog.py` | ran |

## Observed in practice, not verifiable from hermes-agent source

- 5-open-PR cap for users without write access, and the error strings from
  gh, REST and GitHub-App integrations (GitHub-side limit, observed Nov 2026).
- A cosmetic "S-u-d-o Cap" item drawing a `sudo_usage` caution. Verified while building this
  repo: plain mentions of the word in Markdown inside the plugin tree are flagged too.
- ~70 → 11 tool consolidation figures (from the EOH project history).
- Hackathon rules (organiser's announcement), X encoding advice, form quirks.
- Whether tool-code changes need a gateway restart vs a new session depends on how
  Hermes is run. Only the dashboard-route behaviour is source-verified.

## Not verified

- Exact semantics of `requires_plugins`, `python_runtime: external`, `provides_locales`,
  `capabilities` values: taken from docs tables, not exercised.
- Stability of ctx methods beyond `public-api.md`.


## Automated security preflight
`hpd_check` includes a non-executing source security scan. Definite unsafe patterns are errors; ambiguous network fetches, subprocess inheritance and handler result flows are review warnings. Findings contain path/line/rule only, not source text or secret values. This is a heuristic preflight, NOT a security proof: aliases, dynamic imports, wrapper call graphs, DNS pinning, path containment, truthful online behavior and live relay delivery require manual review and adversarial tests. Schema measurement imports trusted plugin code; it is not a sandbox. Run `check_security(Path(...))` alone for untrusted source before opting into code execution.
