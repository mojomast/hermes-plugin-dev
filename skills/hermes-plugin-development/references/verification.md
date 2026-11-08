# Verification log

Re-checked on 2026-11-08 against `NousResearch/hermes-agent` `origin/main` @
`acdc8f1ba6` (2026-11-08), plus the locally installed CLI, **Hermes Agent
v0.22.7** (checkout `b200f5bc60`, 2026-11-03).

The installed checkout is deliberately pinned and is ~2.1k commits behind main,
so claims about newer surfaces were read from `origin/main` with `git show`
rather than from the working tree. Where the two differ, this log says which one
was used — a stale local checkout is not evidence about current Hermes.

## Verified against source / by running

| Claim | Where |
|---|---|
| `register_tool(name, toolset, schema, handler, check_fn, requires_env, is_async, description, emoji, override)`; no `output_schema`; override needs `tools.override` or legacy `allow_tool_override` | `hermes_cli/plugins_context.py`, `hermes_cli/plugins.py::_tool_override_allowed` (main) |
| 50 `ctx` methods incl. provider registrars, `has_capability`, `side_question`, `emit`/`subscribe`, `dispatch_tool` | `hermes_cli/plugins_context.py`, `hermes_cli/plugins_capability_ctx.py`, `hermes_cli/plugins_registrars.py` (main) |
| 46 valid hook names, four return categories, `plugins.hook_callback_timeout` (30 s default; policy hooks fail closed) | `hermes_cli/plugins.py::VALID_HOOKS`; `website/docs/user-guide/features/hooks.md` (main) |
| Capability ids `tools.override`, `llm.{provider,model,agent_id,profile,task}_override`, `llm.side_question`, `gateway.platform_actions`; consent + `granted_capabilities` | `hermes_cli/plugin_capabilities.py`; `developer-guide/plugins/index.md` § Declaring capabilities (main) |
| `plugins.isolation: in_process` (default) vs `host`; refused surfaces; 501/504 dashboard behaviour | `website/docs/user-guide/features/plugins.md` (main); installed checkout has the same section |
| Manifest field allowlist `_KNOWN_MANIFEST_FIELDS`; `provides_middleware` absent from it; `kind` values | `hermes_cli/plugins_manifest.py` (main) |
| `register_skill(name, path, description, frontmatter)` → `<plugin>:<name>`, not copied | `hermes_cli/plugins_content.py` (installed) |
| `plugin_data_dir` / `plugin_db` (profile-aware, WAL) | `plugins/plugin_storage.py` (installed) |
| `agent.secret_scope.get_secret`; catalog credential rule 11 | `agent/secret_scope.py`, `plugin-catalog/README.md` |
| Catalog entry schema, image hosts, ≤6 screenshots, tiers, categories, rules 1–18 | `plugin-catalog/README.md` (main) |
| `scripts/validate_plugin_catalog.py [--json] paths`; unquoted-sha error text | ran it |
| `hermes plugins doctor [target] [--ci]`, `validate path [--install-deps]`, `capabilities` | `hermes_cli/subcommands/plugins.py`; ran doctor + validate |
| New admission lints: core override, desktop surface, private imports (warning), locales, trusted-inbound platforms | `hermes_cli/plugin_validate_*.py` (installed + main) |
| Public plugin API page is generated from `hermes_cli/data/plugin_api.json` | `developer-guide/plugins/public-api.md` header (main) |
| Already-mounted `/api/plugins/<name>/` routes not re-mounted | `hermes_cli/web_server_dashboard.py` (`_plugin_api_mounted`) |
| Rescan endpoint, manifest.json fields (`tab.path`, `position`, `slots`, `css`, `api`) | `extending-the-dashboard.md` |
| Desktop imports limited to `@hermes/plugin-sdk` and `react` | `desktop-plugin-sdk.md` |
| `sudo_usage` pattern + inert-literal handling | `tools/plugin_guard_context.py` |
| Template plugin: pytest green, `hermes plugins validate` "Validation passed", `doctor --ci` OK | ran |
| Template catalog entry passes `validate_plugin_catalog.py` | ran |

## Observed in practice, not verifiable from hermes-agent source

- 5-open-PR cap for users without write access, and the error strings from
  gh, REST and GitHub-App integrations (GitHub-side limit, observed Nov 2026).
- A cosmetic "S-u-d-o Cap" item drawing a `sudo_usage` caution: plain mentions of
  the word in Markdown inside the plugin tree are flagged too.
- ~70 → 11 tool consolidation figures (from the EOH project history).
- Hackathon rules (organiser's announcement), X encoding advice, form quirks.
- Whether tool-code changes need a gateway restart vs a new session depends on how
  Hermes is run. Only the dashboard-route behaviour is source-verified.

## Not verified

- Runtime behaviour of `requires_plugins`, `python_runtime: external`,
  `provides_locales` and `provides_browser_providers` / `provides_web_providers`:
  read from the parser and docs, not exercised.
- The `host` isolation path was not run end to end — only its documented refusal
  list and the 501/504 behaviour were read from source/docs.
- Whether an older release (pre-0.23) enforces every newer admission lint:
  `plugin_validate_private_imports` and `data/plugin_api.json` do not exist in
  the installed 0.22.7 checkout, so that warning is main-only.
- Stability of ctx methods beyond the documented behaviour contract.

## Automated security preflight
`hpd_check` includes a non-executing source security scan. Definite unsafe patterns are errors; ambiguous network fetches, subprocess inheritance and handler result flows are review warnings. Findings contain path/line/rule only, not source text or secret values. This is a heuristic preflight, NOT a security proof: aliases, dynamic imports, wrapper call graphs, DNS pinning, path containment, truthful online behavior and live relay delivery require manual review and adversarial tests. Schema measurement imports trusted plugin code; it is not a sandbox. Run `check_security(Path(...))` alone for untrusted source before opting into code execution.
