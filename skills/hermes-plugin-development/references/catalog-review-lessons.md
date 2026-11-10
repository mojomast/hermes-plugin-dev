# Catalog review lessons (after v0.2.0)

Lessons from catalog reviews and the fix PRs that followed, 8–10 Nov 2026
(America/Toronto). They add to, and do not replace, the admission rules in
`plugin-catalog/README.md` and the contracts in `security-boundaries.md`.

Sources (public review threads; do not comment on them unless the owner asks):

| PR | Plugin | What landed |
|---|---|---|
| [NousResearch/hermes-agent#149691](https://github.com/NousResearch/hermes-agent/pull/149691) | Eye Of Hermes | First-round security items were fixed; a later full-tree re-review blocked on untrusted feed text in the system prompt |
| [#150358](https://github.com/NousResearch/hermes-agent/pull/150358) | Hermagotchi | Pairing approve/revoke must stay pane-only; then a correction blocked dashboard `authedFetch` of absolute asset URLs |
| [#151945](https://github.com/NousResearch/hermes-agent/pull/151945) | hyperrizz | Approved and merged; disclose write-then-execute power; tighten loopback studio servers |
| [#151946](https://github.com/NousResearch/hermes-agent/pull/151946) | stitchslop | Relay token handed out on unauthenticated GETs; `nav` to any URL; wildcard bind |
| [#148687](https://github.com/NousResearch/hermes-agent/pull/148687) | shortrizz | Secrets/child-env/path confinement (closed later to free a catalog slot) |
| [#148018](https://github.com/NousResearch/hermes-agent/pull/148018) | photo-to-part | `pre_tool_call` approval and write confinement; later, hooks must not police every session (also closed to free a slot) |
| [#146230](https://github.com/NousResearch/hermes-agent/pull/146230) | comfyrizz | Portable plugin; merged earlier with no extra review thread |

Reviewers have approved a pin, then come back with a **correction after a full-tree
read** (not just the delta). Budget time for that, and answer point-by-point
(old SHA → new SHA, files, tests).

## 1. Privileged actions stay in the pane

If an online tool can change account access, spend money, approve a device, or
otherwise do something a stranger's lobby message could talk the model into,
**do not let the agent do it**.

Hermagotchi: with `network_enabled` on, `op=pair` accepted a model-supplied
`user_code` / `revoke_device_id`. That mapped to a social action that bypassed
both the autonomy gate and the owner gate, so a DM could get a stranger's
device a session on the user's game account. The fix returns
`unsupported_online` for those fields; approve/revoke stay a **human action in
the pane**. A game-side policy flag is not enough.

Same pattern: Shortrizz Studio reviews picks before render; TempleOS "Take
control" / "Hand back" pauses the agent (`agent_paused`) and shared mode holds
off agent input after the user types or clicks. Put irreversible or
account-level actions behind a real user gesture, a `confirm=true` argument,
and/or Hermes's `pre_tool_call` approval prompt. Refuse those ops inside
`batch`.

Recommended (Eye Of Hermes): frame messages that open links or overwrite the
clipboard should run only after a real click in the pane, not automatically.

## 2. Untrusted third-party text is data, not instructions

Do not tell the model, in a system-prompt section, to "trust" a map line,
watch alert, lobby message, ship name, OSM name, or any other feed you did not
write. Those strings are attacker-controlled (a ship named "ignore previous
instructions…" is enough).

- Strip newlines and control characters from feed titles and messages.
- Present them as quoted data (`title="…"`) under a line that says they are
  third-party text, not instructions.
- Wrap the same text in tool results in a clearly marked field.
- Skills and docs must not contradict the security model (don't tell the model
  it may write a pairing-token file if tokens are pane/hand only).

## 3. Never hand an absolute URL to `authedFetch`

Dashboard `SDK.authedFetch` attaches `X-Hermes-Session-Token`. If asset URLs
from a server (`asset_url: "https://other.host/x.png"`) are passed through, a
compromised or self-hosted server that answers CORS receives the user's
dashboard session token.

Accept only relative paths under the plugin's own routes, plus `data:` /
`blob:`. Never pass an `http(s):` URL to `authedFetch`. Desktop `ctx.rest` is
not affected the same way if assets are mapped to a local route and served as
blob URLs (revoke them when done). Don't rely on future SDK hardening.

Load pane JS from a committed bundle. Import React hooks from `react`, not
`react/jsx-runtime` (a web-app load failure). Never esm.sh / CDN React, never
read parent session tokens, never patch `window.fetch`.

## 4. Loopback relays, viewers, and driven browsers

A token-gated loopback server is only as safe as every route and every bind.

- Require the token on **every** route that can view, drive, or mint access
  (`/`, `/viewer`, `/frame`, `/ping`, `/input`). Do not paste the token into
  an unauthenticated page, and do not return it to `null` or `file://`
  origins.
- Drop `null` and `file://` from origin allowlists. Drop
  `Access-Control-Allow-Private-Network` unless you have a documented need.
- Reject any `Host` that is not the bind address. Compare tokens with a
  constant-time compare (`timingSafeEqual`). Refuse requests that carry an
  unexpected `Origin` when the server is same-machine only.
- Bind `127.0.0.1` by default. Refuse `0.0.0.0` and other public/wildcard
  addresses. A tailnet or non-loopback bind is an explicit, documented
  opt-in with a warning, not a default.
- If the agent can `nav` a dedicated browser, limit destinations to the
  intended origins. Otherwise `file:///…/.hermes/.env` or a LAN admin page
  can be opened and read back through `/frame`.
- Keep the browser sandbox when you are not running as root.
- A loopback studio/app server with no token and no Host/Origin check is the
  same class of bug, even if it only serves a preview.

Store the token mode `0600` under plugin-data; never print it. After a
gateway restart, **reattach** to a still-running sidecar instead of returning
"already running" with no in-process binding.

## 5. Hooks, approval, and session scope

A tool that runs a model-named script (or equivalent) needs a public
`pre_tool_call` hook that returns
`{"action": "approve", "message": "…", "rule_key": "…"}` for that tool and
`None` for everything else. Declare the hook in `provides_hooks`. The
`approve` / `modify` actions need `requires_hermes: ">=0.21.5"` (and
`>=0.23.0` if you also use Desktop `ctx.rest`).

Hooks that fire on **every tool call in every session** must not block the
user's other projects. If you guard evals or log paths, return `None` unless
the target resolves inside *your* checkout (or behind an env flag only your
runner sets). Disclose if you log other tools' names and file paths.

Keep hook callbacks accepting `**kwargs`. Compose multiple behaviours into
one callback when the host keeps one slot per hook name.

## 6. Fetches, children, paths, and errors

The v0.2.0 SSRF / secret-scope / child-env / path contracts still apply, plus:

- **Every** outbound fetch goes through the public-address guard — including
  "internal" place search, research, and provider probes. A leftover
  `urllib.request.urlopen` follows redirects and does a second DNS lookup, so
  it can forward a query-string or `Authorization` key to a private or
  metadata address. POST should not follow redirects. Loopback is opt-in for
  named local services, not for arbitrary user URLs.
- Scrub known secrets and credential-shaped text out of tool `error` /
  `message` / `fix` (and logs). Don't import files whose names look like
  credential files (`.env`, `*-bridge.env`) even when they sit inside
  plugin-data.
- Pin downloaded models and ISOs to a commit or official URL and check
  SHA-256; delete a partial on mismatch. Don't ship large binaries (catalog
  rule 17).
- Confine model-chosen output paths; also honour
  `agent.file_safety.get_write_denied_error` (import lazily so the CLI still
  works outside Hermes). Refuse overwrites unless `overwrite` is set, when
  that is the house style.
- Runtime scripts need runtime dependencies, not just `dev` extras. Keep test
  dependencies out of the install extra Hermes will install. Widen upper
  bounds when the host may ship a newer minor (for example Pillow 13).
- Optional extras (`tiktoken`, `ruamel.yaml`) should skip cleanly in tests
  when missing, with an install hint — not crash CI-unrelated contributor runs.

## 7. Catalog listing, screenshots, and PRs

- At most **6 screenshots**. The catalog page shows 6 and the validator
  refuses 7. `image` (2:1 banner) is separate. Every URL is on a GitHub raw
  host, pinned to the **same** `sha`, and must return HTTP 200.
- Screenshots and demo recordings use **Hermes dark mode**. Fresh scene, no
  hostnames, keys, or private data in frame.
- Video plugins: open on a finished hero frame so frame 0 (and the catalog
  thumbnail) is not blank. Verify delivery checks that.
- YAML-only catalog PR; every SHA bump is a **new** PR showing old → new sha.
- Contributors without write access have at most **5 open PRs** on
  `NousResearch/hermes-agent`. Closing a PR to free a slot is normal; it is
  not a review verdict. Resubmit later.
- After a requested fix, re-pin and (when the owner authorizes a comment)
  reply with a point-by-point delta. Never invent a self-referential catalog
  SHA; the pin is a separate, authorized operation, on an already-existing
  commit, usually a tagged release.
- Reviewers re-check with a **real catalog install in a scratch `HERMES_HOME`**:
  `hermes plugins install <name> --enable`, confirm the installed sha equals
  the pin and every declared tool registers. Do the same yourself before
  asking for a re-review.
- After install or a route change, the Desktop/web app may need
  **Capabilities → Plugins → Rescan**. Enabling the desktop half does not
  import Python by itself; the backend mounts only when the plugin is in
  `plugins.enabled`.
- Scanner cautions on cosmetic names (a "S-u-d-o Cap" style false positive)
  should be explained in the PR body; they do not have to be silent.

## 8. Disclose dangerous power honestly

If a tool can write `scripts/*.mjs` or `package.json` and a later op runs
them with the user's permissions, say so in the description: that is the same
power as file writes plus the terminal. Consider keeping those files
read-only to the write op, and use `npm ci --ignore-scripts` or document that
lifecycle scripts run.

A child hypervisor, a dedicated Chrome, or evaluated user code in a
`SandboxedFrame` is **not** an OS sandbox. Say that in the manifest, README,
and catalog disclosure. Guest networking off stays off if that is the model.

Do not switch security modes from raw process-environment fallbacks
(`PLUGIN_*_ENABLED`) that bypass the documented `config_schema` setting.
Classify online actions as online for autonomy gates; don't label them
`local.*` if they hit the network.

## 9. Live panes must not starve the host

TempleOS: polling `/frame` with a full screendump + OCR on every tick pinned
the Hermes gateway and timed out chat. Serve frames from a **background
cache** (no expensive work on the request path), cap visible fps, back off
when the pane is idle, hidden, or slow, and treat aborted fetches as silent
when the user navigated away. Blob URLs are revoked on the next frame.
Budget the whole serialized capture (see `panes.md`).

A blank, stale, or disconnected pane is not a live-test pass. Bind the pane
to the chat session the SDK exposes.

## 10. Test-host enablement

Before temporarily enabling a plugin on a shared host, snapshot only that
plugin's enablement and settings. After the test, **surgically restore**
those fields — disable the plugin if it was not enabled before. Do not leave
a test enablement on, and do not overwrite the rest of the host config from a
stale backup. Deploy or restart only with permission; keep a rollback SHA.
