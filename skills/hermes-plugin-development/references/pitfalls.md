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
| Old internal imports break after upgrade | Using non-public Hermes modules; the Sep 2026 `_<topic>` module split removed the old paths outright | Import only `public-api.md` names (`hermes_cli/data/plugin_api.json`); `validate` warns on the rest. Old→new map: `COMPAT_MANIFEST.md` |
| `validate`: `no core override` | Rebinding a Hermes function/method/module attribute (`setattr`, `sys.modules[...] =`, `mock.patch`) | Use a hook, middleware, provider profile or Desktop SDK slot; if none fits, request the hook upstream |
| Capability feature does nothing for users | Not declared in `capabilities:`, or declared with a typo (unknown ids are dropped) | Declare it, probe `has_capability`, degrade gracefully; check `hermes plugins capabilities` |
| Plugin refuses to load on a power user's box | They run `plugins.isolation: host`, which refuses platform adapters, approval transports, Telegram/platform handlers, self-SDK model providers, terminal backends, websocket dashboard routes and monkeypatchers | Document "needs `in_process`" in the README; or drop the in-process surface |
| Loader logs `unknown manifest field: provides_middleware` | It is a catalog `capabilities:` key, not a manifest field | Keep it in the catalog entry; remove it from `plugin.yaml` |
| Demo rejected / over time limit | Video ≥ 90 s for hackathon rules | Cut to ~80–88 s; verify duration with ffprobe |


## Catalog review regressions to prevent
- Arbitrary link fetch → centralized DNS-vetted, connection-pinned, redirect-checked SSRF guard.
- Profile-key leakage → secret scope only; no key-reading admin operation or full child environment.
- Blank/unsafe pane → SDK React/auth transport, committed bundles, Desktop ctx.rest plus correct host floor.
- All tools rejected → serialize every registered result with json.dumps, including errors and plaintext feeds.
- Pretend online success → disclose offline practice, gate a real online client, reject unsupported operations.
- Screenshot timeout → budget serialized relay bytes, compress/downscale, check upload responses, deliver explicit errors.
- Works only in checkout → test catalog subdir alone with committed build output and guarded platform imports.
- Test-host settings overwritten → restore only temporary changes, never re-enable user-disabled layers.
