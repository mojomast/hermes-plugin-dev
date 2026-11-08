# Tools, hooks, skills, state and secrets

Source of truth: `hermes_cli/plugins_context.py` (`PluginContext`),
`hermes_cli/plugins_content.py` (`register_skill`), `plugins/plugin_storage.py`,
`agent/secret_scope.py`, and `website/docs/developer-guide/plugins/public-api.md`.

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
- `override=True` replaces a same-named built-in. Requires
  `plugins.entries.<plugin_id>.allow_tool_override: true`, otherwise raises.
- Names already claimed by another toolset are rejected; validate checks
  "built-in tool collisions".

Other `ctx` methods present in the verified source include `register_hook`,
`register_middleware`, `register_command`, `register_cli_command`, `call_mcp`,
`dispatch_tool`, `inject_message`, `post_message`, `ask_choice`, `llm`,
`register_system_prompt_section`, `register_memory_provider`,
`register_platform`, provider registrations (TTS, image/video gen, web search,
browser, terminal), `register_secret_source`, `spawn_task`, `on_unload`,
`get_config`/`set_config`, `state`, `profile_name`. **Check `public-api.md`
before relying on any of these**: presence in source isn't a stability promise.

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

`ctx.register_hook(hook_name, callback, *, hold_stream=False)`. Common names:
`pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`,
`on_session_start`, `on_session_end` (check the docs for the current list).
Accept `**kwargs` in callbacks; payloads grow. If you need several behaviours on
one hook, compose them in a single callback. Declare every hook in `provides_hooks`.

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
Never present a FakeGameClient/demo as a working online integration. Disclose offline simulation and restart persistence in manifest/README/tool descriptions. Online mode requires an explicit user setting such as `network_enabled` and a real authenticated client. Require HTTPS except explicit loopback development; reject credentials in URLs and unsafe redirects/downgrades. Unsupported online operations return a clear `unsupported_operation` JSON error, not fabricated success or silent offline fallback. Test offline defaults, opt-in, authentication, real online read/write effects, disconnects, unsupported ops and persistence independently.
