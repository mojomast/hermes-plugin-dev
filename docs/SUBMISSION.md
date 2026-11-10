# Catalog submission draft — hermes-plugin-dev v0.3.0

**Status: not submitted.** No catalog PR has been opened. No tag or GitHub
release has been created. This file is a draft for Kyle to review.

A version bump in the repo is not permission to tag, release, or pin.

## What is already done

- v0.3.0 landed on branch `feat/v0.3-lessons` (PR against `mojomast/hermes-plugin-dev` main).
- Skill, references, README, CHANGELOG, and `hpd_check` preflight updated.
- `plugin.yaml`, `pyproject.toml`, and `.claude-plugin/plugin.json` all say `0.3.0`.
- Tools: `hpd_scaffold`, `hpd_check`. Hooks: none. Env: none.
- Schema cost at this writing: **2 tools, 190 tokens** (tiktoken `o200k_base`).
- `hermes plugins doctor` / `validate` and a secret scan were run on the branch
  (see the PR). Requires Hermes `>=0.21.6`. Tested against a local Hermes Agent
  **v0.23.0** (`2bd378ed1b8d`).
- Banner: `assets/banner-v3.jpg` (the winged Croc). No additional screenshots
  proposed, so we stay well under the 6-shot cap.

## What still needs Kyle's yes

1. Merge the v0.3.0 PR to main (this file does not authorize that either; it is
   the natural next step once the PR looks good).
2. Tag `v0.3.0` at the merge commit and create the GitHub release.
3. Set `sha` in the catalog entry to that **already-existing** 40-hex commit
   (never invent a self-referential pin). Put the same sha in the banner URL.
4. Confirm `curl -sI` on the banner URL returns HTTP 200.
5. Open a YAML-only PR from a fork of `NousResearch/hermes-agent`, branch
   `catalog/hermes-plugin-dev-v0.3.0`, adding only
   `plugin-catalog/hermes-plugin-dev.yaml`.

### 5-open-PR cap

Contributors without write access can have at most 5 open PRs on
`NousResearch/hermes-agent`. As of 10 Nov 2026 (America/Toronto) these
mojomast catalog PRs were still open and count toward that cap:

- https://github.com/NousResearch/hermes-agent/pull/149691 (Eye Of Hermes)
- https://github.com/NousResearch/hermes-agent/pull/150358 (Hermagotchi)
- https://github.com/NousResearch/hermes-agent/pull/151946 (stitchslop)

That leaves room for this listing without closing one first, but the cap
moves as those land or close. Do not comment on those threads unless asked.

## Draft catalog entry

Copy to `plugin-catalog/hermes-plugin-dev.yaml` after the sha is real.
Leave the placeholder here until step 3 above.

```yaml
name: hermes-plugin-dev
title: Hermes Plugin Dev
repo: https://github.com/mojomast/hermes-plugin-dev
sha: "0000000000000000000000000000000000000000"  # replace with the v0.3.0 tag commit
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
image: https://raw.githubusercontent.com/mojomast/hermes-plugin-dev/<sha>/assets/banner-v3.jpg
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
- **Pinned SHA:** `<40-hex sha>` (tag `v0.3.0`, release: https://github.com/mojomast/hermes-plugin-dev/releases/tag/v0.3.0)
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
- [ ] `hermes plugins validate <checkout> --install-deps` passes
- [ ] `hermes plugins doctor <checkout> --ci` passes
- [ ] Schema token cost: 2 tools, 190 o200k tokens (re-measure at the pin)
- [ ] Banner URL returns HTTP 200 and is pinned to the same SHA; no extra screenshots
- [ ] Secret scan clean
- [ ] Real catalog install in a scratch `HERMES_HOME`: installed sha equals the pin, both tools register
- Tested on Hermes v0.23.0
```

Fill the sha, tick the boxes after they are actually run at the pin, and
re-measure tokens if the schemas change. Do not open the PR until the steps
under "What still needs Kyle's yes" are done.
