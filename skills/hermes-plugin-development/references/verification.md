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

## Observed in catalog reviews (8–10 Nov 2026, America/Toronto)

Not all of these are in hermes-agent source; they are contracts reviewers
enforced on community plugins. Local Hermes CLI at the time of this note:
**Hermes Agent v0.23.0** (`2bd378ed1b8d`).

| Claim | Where it was observed |
|---|---|
| Catalog validator refuses a 7th screenshot; the listing shows at most 6 | teknium1 on Eye Of Hermes #149691 (pushed `8311f912` on the catalog branch to drop one shot) |
| Reviewers may approve, then request changes after a full-tree re-read | #149691 and #150358 "correction to our approval" |
| Pairing approve/revoke (and similar account grants) must be pane-only in online mode; `unsupported_online` for model-supplied codes | teknium1 on Hermagotchi #150358; fixed in mojomast/hermagotchi#9 |
| `SDK.authedFetch` must not be given absolute `http(s):` asset URLs (session token leak) | #150358 correction |
| Untrusted feed text must not be "trust"ed in a system prompt; strip controls; quote as data | #149691 correction |
| Relay token on unauthenticated GET / `null` origins / `0.0.0.0` bind / unconstrained browser `nav` are blockers | stitchslop #151946 |
| Write-then-execute of plugin scripts is listable if disclosed; loopback studio servers should check Host/Origin | hyperrizz #151945 (approved, merged) |
| `pre_tool_call` approval for model-named script runners; write confinement via `get_write_denied_error` | photo-to-part #148018 |
| Session-wide hooks must not block unrelated user projects | #148018 second review |
| 5-open-PR cap; closing a catalog PR to free a slot is normal | #148687 and #148018 closed 9 Nov 2026 by the submitter |
| Reviewers install from the catalog in a scratch home and check sha + tool count | #149691, #150358, #151945 approval notes |
| Dark-mode pane, background frame cache so `/frame` does not starve the gateway, React hooks from `react` | mojomast/hermes-templeos (pane/theme/improvements) |
| Reattach to a live sidecar after a gateway restart | hermes-templeos unreleased notes |
| Video frame 0 / thumbnail should be a finished hero frame, not blank | hyperrizz v2.1.0, shortrizz v0.6.0 |
| Leftover `urlopen` bypasses the SSRF guard; scrub secrets from tool errors | EOH audit PR #29 (open at the time of writing; treat as a required contract) |

The 5-open-PR cap, scanner-on-Markdown behaviour, and ~70 → 11 tool figures
remain "observed in practice" as above.

