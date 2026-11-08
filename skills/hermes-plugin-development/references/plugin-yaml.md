# plugin.yaml reference

Authoritative: `website/docs/developer-guide/plugins/index.md` (manifest v2
reference), `website/docs/developer-guide/plugins/public-api.md` (imports) and
the parser in `hermes_cli/plugins_manifest.py` (`_KNOWN_MANIFEST_FIELDS`).
Verified against `origin/main` @ `acdc8f1ba6` (2026-11-08).

## Minimal (v1, still supported)

```yaml
name: calculator
version: "1.0.0"
description: Math calculator
provides_tools: [calculate]
```

## Manifest v2 (recommended)

`manifest_version: 2` is additive; absent means v1. `api_version` is a separate
axis (runtime ctx/hook generation): keep `1` unless docs say otherwise.

| Field | Notes |
|---|---|
| `name` | `[a-z0-9_-]{1,64}`. Same as the catalog key. |
| `version` | SemVer **string**. Quote it, or YAML may turn `1.10` into `1.1`. |
| `description` | Include disclosure of risky behaviour (network, subprocess, threads, credentials). |
| `author`, `license`, `homepage`, `tags` | Metadata. |
| `provides_tools` | Exact names `register()` registers. Drives validate, catalog chips, search. |
| `provides_hooks` | Same idea for hooks. Compare against `VALID_HOOKS` (`references/hooks.md`). |
| `requires_env` | Strings or `{name, description, url, secret}`. Must be UPPER_SNAKE (validate checks). Install prompts for missing ones. |
| `requires_auth` | e.g. a subscription provider used via `credentialed_provider_request`. |
| `requires_hermes` | SemVer floor (`">=0.21.6"`). Never CalVer, never above the current release. |
| `requires_plugins` | Advisory inter-plugin deps. |
| `python_dependencies` | PEP 508 list. **`pyproject.toml` next to the manifest wins if both exist.** |
| `python_runtime` | `external` when a sidecar manages its own env. |
| `config_schema` | Settings under `plugins.entries.<id>.settings`, rendered as a form in Desktop. Types: str/string, int/integer, float/number, bool/boolean, list/array, dict/object, **secret** (stored in `.env`, never in config.yaml). |
| `config_keys` | Named config keys the plugin reads; shown to the user for consent. |
| `oauth` | Third-party OAuth client; signed in with `hermes auth add <plugin>:<id>`. |
| `capabilities` | Privileged host surfaces. Consent-gated; see `references/capabilities-and-isolation.md`. |
| `provides_locales` | Language packs; each id needs `locales/<id>.yaml` (text leaves only). |
| `kind` | One of `standalone`, `backend`, `exclusive`, `platform`, `model-provider`. Invalid values warn. |
| `platforms` | OS gating metadata, e.g. `[linux, macos]`. |
| `provides_browser_providers`, `provides_web_providers` | Declared provider names for catalog capability matching. |

Fields the parser also recognizes without warning (forward-compat surface, not
behaviour you can rely on): `hooks`, `label`, `optional_env`, `pip_dependencies`,
`external_dependencies`, `emits`, `listens`, `depends`, `hermes`.

`provides_middleware` is **not** in that set. It is a catalog `capabilities:`
key, and `validate` compares it against `register_middleware()` calls — but
writing it in `plugin.yaml` logs `unknown manifest field(s) ignored:
provides_middleware` on every load under v2. Keep it in the catalog entry, not
the manifest.

Unknown keys are tolerated (warning). Real plugins in the wild carry keys like
`permissions:` or `defaults:` that Hermes does not enforce. Don't assume an
invented key does anything — and do not let a typo'd capability id pass
unnoticed: unknown ids are silently dropped from `capabilities:`.

## Dependencies

Put runtime deps in `pyproject.toml` with an **upper bound on every pin**
(`>=1.2,<2`). Hermes's own lock policy doesn't cover plugin deps (catalog rule
10); reviewers flag bare floors.

## Strict YAML

PyYAML keeps the **last** duplicate key without complaint. A second `name:` line
once left a shipped plugin with missing tools. Ship a strict-load test (template
`tests/test_plugin.py`) and bump versions with `scripts/bump_plugin_version.py`,
which refuses duplicate keys and touches only the `version:` line.

## Plugin in a subfolder

Monorepo or app-with-plugin layouts: keep the plugin in e.g. `integration/hermes/`,
install with `hermes plugins install owner/repo/integration/hermes`, and set
`subdir: integration/hermes` in the catalog entry. Optionally put a stub manifest at
the repo root with an impossible `requires_hermes` so a root install refuses
rather than shipping evals/fixtures.


## Review consistency
Declare all credential aliases in `requires_env`, even optional feed providers; retrieve them via secret scope, not process environment. Desktop `ctx.rest` needs a tested `requires_hermes: ">=0.23.0"` floor in manifest and catalog. Describe offline defaults and explicitly gated online/network/autonomy behavior truthfully. Mirror version labels across packaging/portable metadata and catalog; the catalog SHA always pins an already-existing commit.
