# Pitfalls: symptom → cause → fix

| Symptom | Cause | Fix |
|---|---|---|
| Plugin enabled but **0 tools** | `register()` raised, often `TypeError` from an unsupported kw like `output_schema` | Keyword-only calls filtered by `inspect.signature`; fake ctx mirrors the real signature |
| Some tools missing, manifest "looks fine" | Duplicate key in `plugin.yaml` (PyYAML keeps the last) | Strict-load test; bump script that refuses duplicates |
| `validate`: declared tools/hooks mismatch | `provides_*` ≠ registrations | Make them identical; unit test it |
| Catalog validator: `sha 0 must be exactly 40 lowercase hex` | Unquoted all-digit sha parsed as int | Quote `sha` |
| Catalog CI capability failure | Manifest/catalog capabilities ≠ behaviour at the pin | Fix and re-pin |
| Screenshots broken on the docs page | URL not on a GitHub host, not pinned to the sha, or 404 | raw.githubusercontent.com/<owner>/<repo>/<sha>/...; curl each for 200 |
| `CreatePullRequest` permission error / "Resource not accessible by integration" | 5-open-PR cap for non-collaborators, or head not on a fork | Close or land a PR; push to fork; retry or use the web compare page |
| Edited `plugin_api.py`, nothing changed | Existing `/api/plugins/<name>/` route isn't re-mounted | Restart gateway/dashboard |
| New dashboard plugin not visible | Discovery cached per process | `/api/dashboard/plugins/rescan` or restart |
| Key works in shell, not in plugin | Not declared, wrong profile, or a bare process-environment read | `requires_env` + `get_secret` |
| User's disabled layer turns back on | Agent/tool re-applies defaults on load or on request | Persist user toggles; never re-enable without the user |
| State lost after update | State written inside the checkout | `plugin_data_dir` / `plugin_db` |
| Slow turns, context bloat, wrong tool picked | Too many fine-grained tools, verbose schemas | Composable `op` tools; measure o200k delta |
| `sudo_usage` caution in validate | The superuser command word (su+do) in any string, even a cosmetic name | Explain as benign in PR, or rename |
| Root install ships tests/evals/art | Plugin at repo root of a big repo | `subdir:` + install path `owner/repo/subdir` |
| Desktop pane refused in review | Prototype patching, eval, core DOM scraping, app-chunk imports | Stay inside `@hermes/plugin-sdk` |
| Pane APIs fail in frame | Assuming same-origin in `SandboxedFrame` | Use the SDK bridge / backend routes |
| `requires_hermes` rejected | CalVer or higher than current release | SemVer floor you actually tested |
| Deploy broke prod, no way back | No backup / rollback SHA | Record HEAD + back up before every deploy |
| Old internal imports break after upgrade | Using non-public Hermes modules | Only `ctx` and documented public API (`public-api.md`) |
| Demo rejected / over time limit | Video ≥ 90 s for hackathon rules | Cut to ~80–88 s; verify duration with ffprobe |
| Agent approves a stranger's pairing / spends / grants access | Online tool accepted model-supplied codes; autonomy/owner gates bypassed | Return `unsupported_online`; keep approve/revoke/spend **pane-only** (or Hermes approval). A server-side flag is not enough |
| Dashboard session token sent to another host | Absolute `asset_url` passed to `SDK.authedFetch` | Only relative plugin routes (plus `data:`/`blob:`); never `http(s):` to `authedFetch` |
| Model follows a feed as instructions | System prompt said to "trust" watch alerts / lobby text / ship names | Third-party text is quoted data; strip controls; never "trust" it |
| Anyone on the LAN drives the viewer/Chrome | Token on unauthenticated GET; `0.0.0.0` bind; `nav` to any URL; `null` origins | Token on every route; bind loopback; Host check; allowlist nav origins |
| Hook blocks the user's other repos | Global `pre_tool_call` matches common eval/test paths | Return `None` unless the path is inside *your* checkout |
| Model runs a script with no prompt | Dangerous tool registered without an approval hook | `pre_tool_call` → `{"action": "approve", ...}`; declare `provides_hooks` |
| Catalog validator refuses screenshots | More than 6 `screenshots` | At most 6; `image` is separate; all pinned to the sha and HTTP 200 |
| Chat timeouts while the pane is open | `/frame` does expensive capture/OCR on every poll | Background frame cache, cap fps, back off when hidden |
| Web app pane fails to load | React hooks imported from `react/jsx-runtime` | Import hooks from `react` |
| Sidecar "already running" but tools are dead | Gateway restarted; process lived, in-process binding did not | Reattach to the live process |
| Reviewer comes back after approving | Full-tree re-review, not just the delta | Budget for it; reply point-by-point with old → new sha |


## Catalog review regressions to prevent
- Arbitrary link fetch → centralized DNS-vetted, connection-pinned, redirect-checked SSRF guard.
- Profile-key leakage → secret scope only; no key-reading admin operation or full child environment.
- Blank/unsafe pane → SDK React/auth transport, committed bundles, Desktop ctx.rest plus correct host floor.
- All tools rejected → serialize every registered result with json.dumps, including errors and plaintext feeds.
- Pretend online success → disclose offline practice, gate a real online client, reject unsupported operations.
- Screenshot timeout → budget serialized relay bytes, compress/downscale, check upload responses, deliver explicit errors.
- Works only in checkout → test catalog subdir alone with committed build output and guarded platform imports.
- Test-host settings overwritten → restore only temporary changes, never re-enable user-disabled layers.
- Agent-granted pairing / spend / device approve → pane-only or Hermes approval; no model-supplied codes.
- Session token leak via `authedFetch` → relative plugin routes only; never absolute http(s) URLs.
- Feed prompt-injection → untrusted titles are quoted data, never "trust"ed in the system prompt.
- Open relay / wildcard bind / unconstrained browser `nav` → token on every route, loopback bind, Host check, origin allowlist.
- Global hooks police every session → scope to the plugin checkout.
- Catalog listing with 7 screenshots → maximum 6 (validator refuses 7).
- Test enablement left on a shared host → surgically restore prior enablement after the test.
