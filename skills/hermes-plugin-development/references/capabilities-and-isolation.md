# Capabilities and process isolation

Two user-side switches decide what your `ctx` can actually do. Neither is a
sandbox, and both fail closed — so a plugin that assumes it has them is a plugin
that silently does nothing.

Verified against `origin/main` @ `acdc8f1ba6` (2026-11-08):
`hermes_cli/plugin_capabilities.py`, `hermes_cli/plugins_capability_ctx.py`,
`hermes_cli/plugin_isolation.py`, `website/docs/user-guide/features/plugins.md`.

## 1. Capabilities: consent for privileged host surfaces

Declare in `plugin.yaml`, then probe before using:

```yaml
capabilities: [tools.override]
```

```python
def register(ctx):
    if ctx.has_capability("tools.override"):
        ctx.register_tool(..., override=True)
    else:
        ctx.register_tool(..., name="my_write_file")   # non-conflicting fallback
```

- The consent screen appears at install/enable. A later version that adds a
  capability asks again **only for the addition**.
- Undeclared, unknown or unconsented → capability is off. `has_capability`
  returns `False` for unreadable consent state rather than guessing.
- Unknown ids in `capabilities:` are dropped with a warning, so a typo is a
  silent downgrade — check `hermes plugins capabilities` after install.
- `pip`-distributed plugins (no `plugin.yaml` on disk) declare theirs in the
  `hermes_agent.plugin_capabilities` entry-point group, one key per capability
  named `<plugin-id>.<capability-id>`, pointing at the same object as
  `hermes_agent.plugins`.

Known ids and what they unlock (the registry is authoritative):

| Id | Unlocks |
|---|---|
| `tools.override` | `register_tool(..., override=True)` — replace a built-in tool |
| `llm.provider_override` | `ctx.llm` against a provider other than the active one |
| `llm.model_override` | choose the model for host-owned LLM calls |
| `llm.agent_id_override` | attribute LLM calls to another agent id |
| `llm.profile_override` | run LLM calls under a different auth profile |
| `llm.task_override` | route LLM calls through core auxiliary task lanes |
| `llm.side_question` | `ctx.side_question(token, prompt)` — ask the session's own agent after a turn |
| `gateway.platform_actions` | `ctx.platform_actions` — act as the gateway bot |

Legacy per-plugin booleans (`allow_tool_override`, `llm.allow_model_override`,
`allow_platform_actions`, …) still grant the mapped capability but are
deprecated; declaring `capabilities:` is what reviewers and the consent screen
expect. Bundled plugins are trusted for `tools.override` without a grant.

Capabilities are **consent and audit, not containment**: they gate host API
surfaces and nothing else. A plugin that never declares them is not thereby
safe; it simply cannot use those surfaces.

`hermes plugins capabilities` prints declared vs granted per plugin — the first
thing to check when a feature "works in dev" and not for a user.

## 2. `plugins.isolation`: where your code runs

```yaml
plugins:
  isolation: in_process   # default: imported into Hermes
  # isolation: host       # one separate Python process per profile, private pipe
  host:
    launcher: []          # optional argv prefix (sandbox runner)
```

In `host` mode the plugin gets the **same `ctx`** and registers tools, hooks,
slash commands, skills and provider objects as usual; Hermes registers matching
proxies and results cross as the provider base class declares (a secret source's
`fetch()` still receives a `Path` and returns a `FetchResult`). Dashboard plugin
APIs are served by the host.

What that costs you:

- **A few surfaces need in-process code and fail to load with a reason**:
  gateway platform adapters (`register_platform`), approval transports,
  Telegram/platform handlers, model-provider profiles that build their own SDK
  client (`create_client`), terminal backends (their commands fail),
  streaming/websocket dashboard endpoints, and anything that monkeypatches
  Hermes modules. If your plugin is one of these, say so in the README so users
  running `host` know to switch.
- **A crash kills the host, not Hermes.** The in-flight call returns a tool
  error and Hermes restarts the host and reloads plugins with bounded retries —
  so `register()` must be safe to run repeatedly and must not depend on module
  state that the process keeps.
- **No shared interpreter.** Reading another profile's memory, or a core module
  attribute your plugin set earlier, does not work; state belongs in
  `plugin_data_dir` / `plugin_db`.
- **On a multiplex gateway every profile other than the launch profile runs its
  own host anyway**, whatever its config says, and websocket dashboard routes
  for those profiles are refused (HTTP 501); a handler that has not answered in
  60 s gets HTTP 504.

`host` is ordinary profile config, so it is a user choice, not a packaging
requirement. Managed deployments can pin it in `/etc/hermes/config.yaml`.
Test your plugin under `isolation: host` at least once before claiming
"works everywhere" — `hermes plugins doctor` reports which isolation the
current install uses.

## 3. Provider provenance

`register_login_backend` and `register_browser_page_backend` are accepted only
from bundled plugins and catalog installs at tier `verified` or `official`.
A community plugin can ship the same code and have registration refused with a
warning, so do not build a product around them without confirming provenance.
Terminal environment providers cannot shadow built-in backend names (`local`,
`docker`, `modal`, `daytona`, `vercel_sandbox`, `ssh`).
