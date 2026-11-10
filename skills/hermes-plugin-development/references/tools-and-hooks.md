# Tools, hooks, skills, state and secrets

Source of truth: `hermes_cli/plugins_context.py` (`PluginContext`, re-exported
from `hermes_cli/plugins.py`), `hermes_cli/plugins_capability_ctx.py`
(`has_capability`, `side_question`), `hermes_cli/plugins_registrars.py` (the
generated `register_<category>_provider` methods), `hermes_cli/plugins_content.py`
(`register_skill`), `plugins/plugin_storage.py`, `agent/secret_scope.py`, and
`website/docs/developer-guide/plugins/public-api.md`. Verified against
`origin/main` @ `acdc8f1ba6` (2026-11-08).

## register(ctx)

```python
def register(ctx) -> None:
    # fast, offline, no heavy imports; raise nothing for missing optional keys
    ctx.register_tool(name="x", toolset="my-plugin", schema=SCHEMA, handler=handle,
                      description=SCHEMA["description"])
```

If `register()` raises, the plugin ends with no registrations. Treat it as a
pure wiring function.

## register_tool (verified)

```text
register_tool(name, toolset, schema, handler, check_fn=None, requires_env=None,
              is_async=False, description="", emoji="", override=False)
```

- No `output_schema` kw (at least through the verified version). Passing extra
  kwargs raises `TypeError`. Filter kwargs by `inspect.signature`, as the
  template's `_register_tool_compat` does, so the same code runs on older and newer hosts.
- `check_fn`: availability gate (e.g. missing optional key → tool hidden or errors cleanly).
- `override=True` replaces a same-named built-in. It needs the `tools.override`
  capability granted (or the legacy `plugins.entries.<plugin_id>.allow_tool_override: true`);
  otherwise it raises.
- Names already claimed by another toolset are rejected; validate checks
  "built-in tool collisions".

## The `ctx` surface (verified, 50 methods)

`register_tool` and the rest of the 0.1 generation are still there; the list
grew. Grouped, not alphabetical, because that is how you pick one:

| Want to… | Method |
|---|---|
| expose a tool | `register_tool` |
| react to a turn / tool / stream | `register_hook`, see `hooks.md` |
| change behaviour instead of observing | `register_middleware(kind, callback)` |
| add a slash command | `register_command(name, handler, ...)`, `register_cli_command` |
| run a host-owned LLM call | `llm` (see `plugin-llm-access.md`), `side_question` (capability `llm.side_question`), `subagent_lifecycle`, `delegation_backends`, `current_cron_execution` |
| reach MCP | `call_mcp(server, tool, arguments, timeout)` — default-deny |
| call another registered tool | `dispatch_tool(name, args, **kw)` |
| talk to the user mid-turn | `inject_message`, `post_message`, `ask_choice` |
| steer the prompt | `register_system_prompt_section` (cached; prefer over `pre_llm_call`) |
| ship a skill | `register_skill(name, path, description, frontmatter)` |
| persist | `plugin_data_dir` / `plugin_db` (below), `state`, `get_config` / `set_config` |
| know where you are | `plugin_id`, `profile_name`, `session_cwd`, `session_surface`, `has_plugin(id)` |
| check consent | `has_capability(id)` — `references/capabilities-and-isolation.md` |
| run background work | `spawn_task(coro, name=...)`, `on_unload(callback)` |
| emit/subscribe internal events | `emit(event, payload)`, `subscribe(event, callback)` |
| register a provider | `register_{image_gen,video_gen,web_search,browser,tts,transcription,delegation,terminal_environment,secret_source}_provider*`, `register_memory_provider`, `register_context_engine`, `register_context_reference`, `register_dashboard_auth_provider`, `register_login_backend`, `register_browser_page_backend`, `register_platform`, `register_platform_handler`, `register_telegram_handler`, `register_slack_action_handler`, `register_auxiliary_task`, `register_approval_transport`, `register_redaction_patterns`, `register_locale`, `register_locale_dir` |

`register_secret_source` takes a `source=`, not a `provider=`. The provider
methods are **generated** from `hermes_cli/plugins_registrars.py`; each type-checks
the object, registers it in a profile-scoped registry, and is removed on unload.
Two of them (`register_login_backend`, `register_browser_page_backend`) are
refused for community installs — see the provenance note in
`references/capabilities-and-isolation.md`.

**Check `public-api.md` before importing anything else from Hermes**: the page is
generated from `hermes_cli/data/plugin_api.json`, and `validate` warns (rule 9)
on every Hermes import outside it. Presence of a method in source is not a
stability promise; documented behaviour is.

## Schema design and token budget

Each exposed tool schema costs context on every turn.

- Prefer **composable tools**: one tool per domain with an `op` enum, rather than
  one tool per verb. A map plugin dropped from ~70 tools to 11 this way.
- Descriptions say *when* to call and *when not to*. Keep enums tight; put rare
  options behind something like `detail: "full"`.
- Measure: `json.dumps(schemas, separators=(",", ":"))` → tiktoken `o200k_base`.
  Record before/after in the PR or changelog (template `scripts/measure_schemas.py`).
- Errors: `{"ok": false, "code": "...", "error": "...", "fix": "..."}`.

## Hooks

`ctx.register_hook(hook_name, callback, *, hold_stream=False)`. 46 valid names at
the verified commit; the full list, the four return shapes (observer /
transform / directive / policy) and the timeout rules are in `hooks.md`.
Accept `**kwargs` in callbacks; payloads grow additively. If you need several
behaviours on one hook, compose them in a single callback. Declare every hook in
`provides_hooks`.

A tool that runs a model-named script (or anything with equivalent power) must
go through Hermes's approval prompt: register `pre_tool_call`, and when
`tool_name` matches, return
`{"action": "approve", "message": "Run <script> <args> in <cwd>", "rule_key": "<tool>"}`.
Return `None` for every other tool. The `approve`/`modify` actions first ship
in Hermes 0.21.5; declare `requires_hermes: ">=0.21.5"` (and `>=0.23.0` if
you also use Desktop `ctx.rest`).

Hooks that fire on every tool call in every session must not police the user's
other projects. If you guard eval paths or log calls, return `None` unless the
target resolves inside your plugin checkout (or behind an env flag only your
runner sets). Disclose it if you log other tools' names and file paths.

## Bundled skills

```python
ctx.register_skill(name, path, description="", frontmatter=None)
```

Read-only, resolvable as `<plugin_name>:<name>` via `skill_view`, listed in
`skills_list` while enabled, not copied into `~/.hermes/skills/`. `name` must not
contain `:`. Document the exact id in your README. Update skill text whenever you
rename or merge tools.

## State

`from plugins.plugin_storage import plugin_data_dir, plugin_db`

- `plugin_data_dir(name)` → `<HERMES_HOME>/plugin-data/<name>/`, created on demand and
  profile-aware (don't cache across profile switches).
- `plugin_db(name, filename="data.db")` → sqlite in WAL mode, safe for a dashboard
  reader alongside a tool writer.
- Never store state in the plugin checkout; `hermes plugins update` replaces it.
- Persist user "off" switches (disabled layers, features, autonomy) and never
  flip them back on yourself: not on restart, update, or agent request.

## Secrets (catalog rule 11)

- Declare in `requires_env` (or as a `config_schema` secret). Read with
  `agent.secret_scope.get_secret(NAME)`, which respects the active profile.
- Don't fall back to reading `.env` files, the process environment directly, Hermes
  `auth.json`, vendor CLI token files, browser profiles or keychains.
- Subscription sign-in: `credentialed_provider_request` + `requires_auth`; Hermes
  attaches the token, the plugin never sees it.
- Third-party OAuth: declare `oauth:` in the manifest; https-only endpoints.
- Loopback relays/sidecars: bind `127.0.0.1`, gate with a random token stored mode
  `0600` in plugin-data, never print it.

## LLM and MCP access

Use host-owned `ctx.llm` (see `plugin-llm-access.md` in the docs) instead of
embedding your own agent runtime. `ctx.call_mcp(...)` is default-deny until the
operator allowlists it for your plugin.


## Tool result wire contract
Every registered handler returns a STRING: `json.dumps(envelope)`, on success, validation failure, exception and unsupported operation. Internal helpers may return dictionaries, but serialize at the registered boundary. Test `isinstance(result, str)` then `json.loads(result)` for every op. Never forward CSV/plaintext upstream feeds directly: wrap them in JSON envelopes, e.g. `{"ok": true, "format": "csv", "data": text}` (including FIRMS/AIS-style responses). Do not stringify dictionaries with `str(dict)`.

## Honest offline and online clients
Never present a FakeGameClient/demo as a working online integration. Disclose offline simulation and restart persistence in manifest/README/tool descriptions. Online mode requires an explicit user setting such as `network_enabled` and a real authenticated client. Require HTTPS except explicit loopback development; reject credentials in URLs and unsafe redirects/downgrades. Unsupported online operations return a clear `unsupported_operation` or `unsupported_online` JSON error, not fabricated success or silent offline fallback. Test offline defaults, opt-in, authentication, real online read/write effects, disconnects, unsupported ops and persistence independently.

Privileged online actions — approving or revoking a pairing, spending, granting
a device session — stay **pane-only** (or behind Hermes's approval prompt). Do
not accept a model-supplied code for those ops; a server-side policy flag is
not enough, because the trigger can come from another player's message.
Classify online effects as online for autonomy gates (`local.*` is the wrong
bucket). Do not flip security modes from raw process-environment fallbacks
that bypass the documented `config_schema` setting.

Third-party feed text (alerts, lobby messages, ship names, OSM names) is
untrusted data: strip newlines and control characters, wrap it in a marked
field, and never tell the model in a system-prompt section to "trust" it.

If a tool can write scripts or `package.json` and a later op executes them
with the user's permissions, say so in the description. That is file-write
plus terminal power. Scrub secrets and credential-shaped text out of `error`
/ `message` / `fix` before they leave the handler.
