# Catalog submission draft — hermes-plugin-dev v0.3.0

**Status: ready to open, waiting for Kyle's yes.** The plugin v0.3.0 tag and
GitHub release exist. The catalog PR on `NousResearch/hermes-agent` has **not**
been opened.

- Plugin repo: https://github.com/mojomast/hermes-plugin-dev
- Merge commit / **catalog pin:** `1bc5bf5142db3bfc3c0cdf032a7adb4883426825`
- Tag: https://github.com/mojomast/hermes-plugin-dev/releases/tag/v0.3.0
- This file and `catalog/hermes-plugin-dev.yaml` were updated *after* the tag
  so they could carry the real sha. The pin still points at the tagged commit,
  not at this docs follow-up.

## Already done

- Merged [mojomast/hermes-plugin-dev#1](https://github.com/mojomast/hermes-plugin-dev/pull/1) (merge commit `1bc5bf5142db3bfc3c0cdf032a7adb4883426825`).
- Tagged `v0.3.0` on that commit and published the GitHub release.
- Banner at the pin returns HTTP 200:
  https://raw.githubusercontent.com/mojomast/hermes-plugin-dev/1bc5bf5142db3bfc3c0cdf032a7adb4883426825/assets/banner-v3.jpg
- Tools: `hpd_scaffold`, `hpd_check`. Hooks: none. Env: none.
- Schema cost: **2 tools, 190 tokens** (tiktoken `o200k_base`).
- `hermes plugins doctor . --ci` and `hermes plugins validate .` were green on
  the release tree. Security scan: **safe**. Requires Hermes `>=0.21.6`. Local
  CLI used for those checks: Hermes Agent v0.23.0 (`2bd378ed1b8d`).
- No extra screenshots (under the 6-shot cap).

## Still needs Kyle's yes

Open a YAML-only PR from the fork branch (see below) to
`NousResearch/hermes-agent`, adding only `plugin-catalog/hermes-plugin-dev.yaml`.
Do not comment on other catalog threads unless asked.

## Draft catalog entry

This is the file to copy to `plugin-catalog/hermes-plugin-dev.yaml`.

```yaml
name: hermes-plugin-dev
title: Hermes Plugin Dev
repo: https://github.com/mojomast/hermes-plugin-dev
sha: "1bc5bf5142db3bfc3c0cdf032a7adb4883426825"
subdir: ""
description: >-
  Build Hermes plugins with Hermes: bundles the hermes-plugin-development skill plus two
  offline tools to scaffold a plugin from a validated template and lint manifests, catalog
  entries, security preflight and schema token cost. No network, subprocesses or credentials;
  writes only into the target folder you name; the lint imports the target plugin's
  register() with a fake host. The security preflight is a heuristic, not a proof.
maintainer: mojomast
tier: community
category: tools
requires_hermes: ">=0.21.6"
version: "0.3.0"
docs_url: https://github.com/mojomast/hermes-plugin-dev#readme
readme: true
platforms: []
image: https://raw.githubusercontent.com/mojomast/hermes-plugin-dev/1bc5bf5142db3bfc3c0cdf032a7adb4883426825/assets/banner-v3.jpg
known_issues: []
capabilities:
  provides_tools: [hpd_scaffold, hpd_check]
  provides_hooks: []
  provides_middleware: []
  requires_env: []
```

## Draft PR title

`plugin-catalog: add Hermes Plugin Dev v0.3.0`

## Draft PR body

```markdown
## plugin-catalog: add Hermes Plugin Dev v0.3.0

Adds `plugin-catalog/hermes-plugin-dev.yaml` (YAML-only diff).

- **Repo:** https://github.com/mojomast/hermes-plugin-dev
- **Pinned SHA:** `1bc5bf5142db3bfc3c0cdf032a7adb4883426825` (tag `v0.3.0`, release: https://github.com/mojomast/hermes-plugin-dev/releases/tag/v0.3.0)
- **Subdir:** none (repo root)
- **Maintainer:** @mojomast (owner of the plugin repo)

### What it does

A skill plus two offline tools for building Hermes plugins. The bundled
`hermes-plugin-development` skill covers manifests, `register(ctx)`, panes,
secrets, doctor/validate, catalog pins, and the review contracts learned
from shipping community plugins. `hpd_scaffold` writes a validated template
into an empty directory. `hpd_check` lints a plugin's manifest, registrations,
security preflight, catalog entry and o200k schema cost. The lint's token
measure imports the target `register()` with a fake host, like `hermes plugins
doctor` does. The security preflight is a heuristic, not a proof.

### Capabilities (match the pin)

- Tools (2): `hpd_scaffold`, `hpd_check`
- Hooks: none
- Env / secrets: none

### Disclosure

No network, no subprocesses, no credentials, no background threads. Writes
only inside the `target_dir` you pass to `hpd_scaffold` (refuses a non-empty
directory). `hpd_check` is read-only except for importing trusted plugin
code during schema measurement.

### Checks run at the pinned SHA

- [ ] `python scripts/validate_plugin_catalog.py plugin-catalog/hermes-plugin-dev.yaml` passes
- [x] `hermes plugins validate` at the pin passes (security scan: safe)
- [x] `hermes plugins doctor . --ci` at the pin passes (2 tools, 0 hooks)
- [x] Schema token cost: 2 tools, 190 o200k tokens
- [x] Banner URL returns HTTP 200 and is pinned to the same SHA; no extra screenshots
- [x] Secret scan clean
- [ ] Real catalog install in a scratch `HERMES_HOME`: installed sha equals the pin, both tools register
- Tested on Hermes v0.23.0
```
