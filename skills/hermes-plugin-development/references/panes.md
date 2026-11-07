# Dashboard and desktop panes

Docs: `website/docs/user-guide/features/extending-the-dashboard.md` and
`website/docs/developer-guide/desktop-plugin-sdk.md`. Implementation:
`hermes_cli/web_server_dashboard.py`.

## Web dashboard tab (`dashboard/`)

```text
dashboard/
├── manifest.json    # name, label, tab{...}, entry, optional slots, css, api
├── dist/index.js    # IIFE bundle using window.__HERMES_PLUGIN_SDK__
├── dist/style.css   # optional
└── plugin_api.py    # optional FastAPI router → /api/plugins/<name>/
```

```json
{ "name": "my-plugin", "label": "My Plugin",
  "tab": { "path": "/my-plugin", "position": "after:skills" },
  "slots": ["sidebar"], "entry": "dist/index.js", "css": "dist/style.css",
  "api": "plugin_api.py" }
```

(Field names match the docs examples; check the docs for the current `tab` keys.)

- Use `SDK.React`, `SDK.components`, `SDK.fetchJSON`. Don't bundle your own React.
- Discovery is cached per dashboard process. New plugin → `GET
  /api/dashboard/plugins/rescan` or restart `hermes dashboard`.
- **Changing an existing plugin's `plugin_api.py`:** the server checks its route table and
  skips a prefix that's already mounted (`_plugin_api_mounted`). Edits don't take effect
  until you restart the gateway/dashboard process. Plan that restart into deploys.
- With `plugins.isolation: host`, plugin APIs run in a separate plugin-host process
  per profile, not inside the gateway. Don't rely on shared in-process globals between
  tools and dashboard routes; share state via `plugin_data_dir` / `plugin_db`.
- Bundle size and frame rate matter. Lazy-load heavy layers and keep polling intervals sane.

## Desktop / webapp pane (`desktop/plugin.js`)

- The only importable specifiers are `@hermes/plugin-sdk` and `react` (plus whatever
  the SDK doc lists for the verified version).
- Guest content runs in `SandboxedFrame`: opaque origin, scripts only. Talk over the
  documented message / tool-call bridge; don't depend on same-origin, cookies, or
  `allow-same-origin`.
- Catalog rule 8: no prototype patching, no `eval`/`new Function`, no importing app
  chunks, no scraping or styling core UI DOM.
- Bind the pane to the chat session the SDK exposes, so the agent's tool calls drive
  the pane next to that chat.

## Agent ↔ pane patterns

| Need | Pattern |
|---|---|
| UI → backend | `SDK.fetchJSON("/api/plugins/<name>/...")` |
| Agent → UI | Tool writes state (plugin-data / sidecar); pane polls or subscribes |
| UI → agent context | `pre_llm_call` hook injecting a compact context line, or tool results |

Live-music example: one tool composes code, the pane plays it after the user presses
Play, and a bad edit is rejected without stopping the current loop. Evaluated user code
stays in the sandboxed frame (disclose that it's not an OS sandbox).

## Pane UX lessons

- Respect user toggles: if the user hides a layer or panel, the agent must not
  re-enable it. Store the choice and check it before every agent-driven change.
- Make dark mode work; demos and screenshots look better in it.
- Give each agent action visible feedback in the pane (highlight, toast); it makes
  demos legible.
