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

- Respect user toggles: if the user hides a layer, panel, or companion, the
  agent must not re-enable it. Store the choice and check it before every
  agent-driven change. Offer a hide toggle for optional chrome; a hard-off
  setting is fine in addition to the toggle.
- **Dark mode is the default** for plugin UI, docs screenshots, and demo
  recordings. Hermes itself is used in dark mode; catalog shots should match.
- Give each agent action visible feedback in the pane (highlight, toast); it
  makes demos legible.
- Shared screens need an input arbiter: Watch / Shared / Take control, with
  **Hand back**. Shared mode should hold off agent input briefly after the
  user types or clicks. Agent tools return a clear `agent_paused` (or
  equivalent) while the user has control.
- Privileged account actions (pairing approve/revoke, spending, opening
  arbitrary links, overwriting the clipboard) need a **real user gesture** in
  the pane, not a model-only tool call. See `catalog-review-lessons.md`.
- Import React hooks from `react`, not `react/jsx-runtime`, or the web app
  pane can fail to load.
- Do not starve the Hermes gateway. Serve live frames from a background cache
  (no OCR / heavy encode on the request path), cap visible polling (a few
  fps), back off when the pane is idle, hidden, or the host is slow, and
  ignore aborted fetches when the user navigated away. Revoke blob URLs on
  the next frame. After a gateway restart, reattach to a still-running
  sidecar instead of "already running" with no binding.
- After install or a route change, the user may need **Capabilities → Plugins
  → Rescan**. Enabling the desktop half does not import Python by itself; the
  backend mounts only when the plugin is in `plugins.enabled`.

## Catalog review safety contract
Dashboard: ship reproducibly built `dashboard/dist/index.js` at the pinned commit, with sources and lockfile. Use `window.__HERMES_PLUGIN_SDK__.React` (import hooks from `react`, not `react/jsx-runtime`) and `SDK.authedFetch`/documented `SDK.fetchJSON`. Never load React/code from esm.sh or another CDN, read session tokens or grants from parent globals/localStorage/sessionStorage, or monkeypatch `window.fetch`. Host authentication belongs to the SDK. **Never pass an absolute `http(s):` URL to `authedFetch`** — only relative plugin routes, plus `data:`/`blob:`. An upstream `asset_url` on another host would receive `X-Hermes-Session-Token`.

Desktop: route ALL host API calls through `ctx.rest('/proxy/v1/...')`; never extract stored grants or attach raw authorization headers. Load assets through JSON routes via `ctx.rest`, decode into Blob URLs, and revoke URLs when no longer needed. Bundle `desktop/plugin.js`; set `requires_hermes: ">=0.23.0"` when using this transport (and mirror the floor in catalog metadata). Do not mix dashboard and Desktop transports. Test both surfaces, including asset load failures and unauthenticated errors.

## Capture and pane-to-host results
Document and test the actual relay request-body limit. One reviewed relay accepted 512 KiB, less than a full-size PNG. Budget the WHOLE serialized JSON payload, including the 4/3 expansion of binary payloads, UTF-8 and envelope overhead; leave headroom. Downscale and compress captures before upload, progressively reducing size/quality within a bounded retry budget. Reject still-oversize results explicitly. Check HTTP status/response, never swallow a failed upload. Complete the pending command with a structured error on capture, encode, upload, disconnect or size failure rather than waiting for a timeout. Test just-below/above limits and non-2xx replies. Verify the deployed pane bundle actually contains the fix and reconnect it after restart.

## Loopback relays and driven browsers

Token-gate every route that can view, drive, or mint access — including `/`,
`/viewer`, `/frame`, `/ping` and `/input`. Do not put the token in an
unauthenticated page or return it to `null` / `file://` origins. Drop those
origins from allowlists. Bind `127.0.0.1` by default; refuse `0.0.0.0` and
other wildcard/public addresses (tailnet bind is an explicit, documented
opt-in). Reject a `Host` that is not the bind address; compare tokens in
constant time; treat an unexpected `Origin` as hostile on a same-machine
server. If a tool can navigate a dedicated browser, allowlist the intended
origins only. Keep the browser sandbox when not running as root. See
`catalog-review-lessons.md`.
