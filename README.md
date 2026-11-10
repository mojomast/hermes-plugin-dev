<p align="center">
  <img src="assets/banner-v3.jpg" alt="Hermes Plugin Dev: a skill + plugin for building Hermes plugins" width="100%">
</p>

<h1 align="center">hermes-plugin-dev</h1>

<p align="center">
  <b>Teach any coding agent to ship Hermes Agent plugins that pass review the first time.</b><br>
  One Agent Skill + one Hermes plugin, distilled from shipping real community plugins
  and from the catalog reviews that followed.
</p>

<p align="center">
  <a href="https://github.com/mojomast/hermes-plugin-dev/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/mojomast/hermes-plugin-dev/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="https://agentskills.io"><img alt="Agent Skills" src="https://img.shields.io/badge/Agent%20Skills-compatible-8A2BE2"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img alt="Hermes Agent" src="https://img.shields.io/badge/Hermes%20Agent-%E2%89%A50.21.6-black"></a>
  <img alt="Version 0.3.0" src="https://img.shields.io/badge/version-0.3.0-8b5cf6">
  <img alt="Tool schema cost" src="https://img.shields.io/badge/tool%20schemas-190%20o200k%20tokens-success">
</p>

---

## Why this exists

[Hermes Agent](https://github.com/NousResearch/hermes-agent) has a powerful plugin
system and a reviewed plugin catalog. Getting a plugin from idea to listed means
learning a dozen sharp edges the hard way:

- a stray keyword to `register_tool` and your plugin silently loads with **0 tools**
- a duplicated YAML key that PyYAML quietly "fixes" for you
- an unquoted commit SHA the catalog validator reads as a number
- a dashboard API change that won't show up until you restart the gateway
- a security scan that fails your plugin because your *README* mentions a scary command word
- a PR that won't open because of a GitHub limit, not your auth
- an agent tool that can approve a stranger's device because a lobby message talked it into it
- a session token that leaks because `authedFetch` was handed an absolute asset URL
- a loopback "token-gated" viewer that hands the token to anyone who asks
- a live pane that starves the Hermes gateway because every poll runs a full capture

This repo captures those lessons (each **checked against hermes-agent source** or
against the public catalog review threads, with a
[verification log](skills/hermes-plugin-development/references/verification.md))
in a format every major coding agent can load. When installed into Hermes, it
also gives the Hermes agent two small tools to build plugins itself.

## What's inside

| | |
|---|---|
| 🧠 **Agent Skill** | [`skills/hermes-plugin-development/`](skills/hermes-plugin-development/SKILL.md): a short core guide plus deep-dive references (manifest, `ctx` API, panes, testing, release & catalog, review lessons, pitfalls, hackathons, worked examples, verification). |
| 🧩 **Template plugin** | [`templates/hello-hermes`](skills/hermes-plugin-development/templates/hello-hermes): a minimal plugin that passes `hermes plugins validate` and `doctor --ci` as-is, with a fake-host test, strict-YAML check, version bump script and schema-token meter. |
| 📋 **Catalog kit** | [Catalog entry](skills/hermes-plugin-development/templates/catalog/plugin-catalog-entry.yaml) and [PR body](skills/hermes-plugin-development/templates/catalog/PR_BODY.md) templates matching the upstream schema, including the 6-screenshot cap. |
| 🛠️ **Hermes plugin** | `plugin.yaml` + `register(ctx)` at the repo root: bundles the skill and adds **2 lean tools** (190 o200k tokens total, measured with tiktoken `o200k_base`). |

### The two tools

| Tool | What it does | Safety |
|---|---|---|
| `hpd_scaffold(target_dir, name)` | Creates a new plugin from the template, renamed, with a catalog entry + PR body stub | Writes only inside `target_dir`; refuses non-empty dirs; never overwrites |
| `hpd_check(path, catalog_entry?)` | Offline lint: strict YAML, manifest rules, `provides_tools` vs registered, security preflight, schema token cost, catalog entry rules (sha, hosts, category, subdir, at most 6 screenshots) | Read-only. Token measure imports the target's `register()` with a fake host, the same as `hermes plugins doctor` |

No network calls, no subprocesses, no git, no credentials. The security preflight
is a heuristic, not a proof: it flags known anti-patterns (CDN React, session-token
reads, absolute URLs to `authedFetch`, inherited child environments, wildcard binds,
and more) without printing source or secret values.

## What the skill teaches

- Manifest v2, strict YAML, and keeping `provides_tools` identical to `register()`.
- Keyword-only `ctx.register_tool`, JSON-string results, and lean `op` enums measured in o200k tokens.
- Dashboard and Desktop panes: SDK-only, `SandboxedFrame`, `ctx.rest` on Hermes `>=0.23.0`, dark mode, shared-screen arbiters, gateway-safe frame polling.
- Secrets through `agent.secret_scope.get_secret`, minimal child environments, path confinement, SSRF-safe fetches.
- Catalog review contracts: pane-only privileged actions, no "trust" for feed text, no absolute URLs to `authedFetch`, token-gated loopback relays, hook scope, `pre_tool_call` approval, at most 6 screenshots, scratch-home install checks.
- Release hygiene: quote the 40-hex sha, YAML-only catalog PRs, the 5-open-PR cap, no invented pins, restore enablement on a shared test host.

The core is in [`SKILL.md`](skills/hermes-plugin-development/SKILL.md). Open the
[references](skills/hermes-plugin-development/references/) when you need the
worked detail.

## 60-second quickstart

**In Hermes:**

```bash
hermes plugins install mojomast/hermes-plugin-dev
hermes plugins enable hermes-plugin-dev
```

Then ask your agent: *"Scaffold a Hermes plugin called weather-now in ~/code/weather-now,
then check it."* It loads `hermes-plugin-dev:hermes-plugin-development`, calls
`hpd_scaffold` and `hpd_check`, and tells you to run `doctor` and `validate`.

**Any other agent (Claude Code, Codex, Cursor, …):**

```bash
npx skills add mojomast/hermes-plugin-dev
```

Then: *"Using the hermes-plugin-development skill, build me a Hermes plugin that …"*

## Install matrix

| Agent | Install |
|---|---|
| **Hermes Agent** | `hermes plugins install mojomast/hermes-plugin-dev` then `hermes plugins enable hermes-plugin-dev` (skill id `hermes-plugin-dev:hermes-plugin-development`) |
| **Claude Code** (plugin) | `/plugin marketplace add mojomast/hermes-plugin-dev` then `/plugin install hermes-plugin-dev@hermes-plugin-dev` |
| **Claude Code** (plain skill) | `git clone https://github.com/mojomast/hermes-plugin-dev && cp -r hermes-plugin-dev/skills/hermes-plugin-development ~/.claude/skills/` |
| **skills CLI** (Claude Code, Codex, Cursor, OpenCode, Goose, Windsurf, Hermes, …) | `npx skills add mojomast/hermes-plugin-dev` (add `-g` for global, `-a <agent>` to target one) |
| **Cursor** | Copy `skills/hermes-plugin-development` into `.cursor/skills/` (project) or `~/.cursor/skills/` |
| **Codex / AGENTS.md agents** | Vendor the folder and add to `AGENTS.md`: *"Before working on a Hermes plugin, read `skills/hermes-plugin-development/SKILL.md`."* |
| **Anything else** | Attach `SKILL.md` as context; the agent opens `references/` and `templates/` on demand |

## Example session

```text
you   ▸ Make a Hermes plugin that exposes my local Ollama models as a tool.
agent ▸ (loads hermes-plugin-development skill)
        hpd_scaffold → ~/code/ollama-models   ✓ 11 files
        …edits __init__.py: one composable tool `ollama_models(op=list|show)`…
        hpd_check    → manifest ✓  tools match ✓  schema tokens reported
        Run: hermes plugins doctor ~/code/ollama-models --ci
             hermes plugins validate ~/code/ollama-models --install-deps
```

## Catalog submission checklist

Use this when *your* plugin is ready to list. A draft catalog entry and PR body
for *this* repo live in [`docs/SUBMISSION.md`](docs/SUBMISSION.md) — that
catalog PR has **not** been opened.

1. Tests, `hermes plugins doctor . --ci`, and `hermes plugins validate . --install-deps` are green at the commit you will pin.
2. Schema tokens measured with tiktoken `o200k_base` and recorded.
3. Secret scan is clean. No `.env`, tokens, or pane-captured keys in the tree.
4. README discloses network, subprocesses, credentials, and any write-then-execute or hypervisor/browser power. Versions match across `plugin.yaml`, `pyproject.toml`, and packaging metadata.
5. At most 6 screenshots, plus an optional 2:1 banner, all on GitHub raw hosts, pinned to the same 40-hex `sha`, each returning HTTP 200, shot in Hermes dark mode.
6. YAML-only PR on a fork of `NousResearch/hermes-agent`, branch `catalog/<name>-vX.Y.Z`. Never invent the sha; pin an already-existing (usually tagged) commit.
7. A real `hermes plugins install <name> --enable` in a scratch `HERMES_HOME` installs that sha and registers every declared tool.
8. If you have a pane: it is connected to the right session; privileged actions are pane-only or approval-gated; a temporary enable on a shared host is restored afterwards.
9. Watch the 5-open-PR cap on `NousResearch/hermes-agent`. A version bump in this repo is not a tag, a release, or a catalog PR — those need an explicit yes.

## Use the checks without Hermes

```bash
git clone https://github.com/mojomast/hermes-plugin-dev && cd hermes-plugin-dev
pip install pyyaml tiktoken
python -c "import hpd_core, json; print(json.dumps(hpd_core.check('/path/to/my-plugin', 'catalog/my-plugin.yaml'), indent=2))"
```

## Repository layout

```text
hermes-plugin-dev/
├── plugin.yaml  __init__.py  hpd_core.py   # the Hermes plugin
├── skills/hermes-plugin-development/        # the Agent Skill
│   ├── SKILL.md
│   ├── references/*.md
│   └── templates/{hello-hermes,catalog}/
├── .claude-plugin/{plugin.json,marketplace.json}
├── catalog/hermes-plugin-dev.yaml           # prepared catalog entry (not yet submitted)
├── docs/SUBMISSION.md                       # draft catalog PR, pending review
├── CHANGELOG.md
├── tests/                                   # fake-host tests, no Hermes needed
└── .github/workflows/ci.yml                 # pytest + gitleaks
```

## FAQ

**Is this an official Nous Research project?** No. It's a community project. Upstream docs
and source always win; the skill says so and links them.

**Will it go stale?** Hermes moves fast. Every claim is tagged in the
[verification log](skills/hermes-plugin-development/references/verification.md) with the
Hermes version or catalog review it was checked against, and unverified items are marked.
PRs welcome.

**Why only two tools?** Every tool schema costs context on every turn. Two composable tools
(190 o200k tokens) cover scaffolding and linting. Running `doctor`/`validate` stays in your
terminal, where Hermes's own checks are authoritative.

**Does it run my plugin's code?** Only `hpd_check`'s token measure, which imports your
`register()` with a fake host, like `hermes plugins doctor` does. Only check code you trust.
The security preflight reads source without executing it; run `check_security()` alone
before opting into code execution on an untrusted tree.

**Is it in the Hermes catalog yet?** Not at the time of v0.3.0. The entry is prepared
under `catalog/` and drafted in `docs/SUBMISSION.md`. A catalog PR will be opened only
after an authorized tag and pin.

## Contributing

Found a new pitfall? Add it to
[`references/pitfalls.md`](skills/hermes-plugin-development/references/pitfalls.md) with the
symptom, cause and fix, and note in `verification.md` how you confirmed it. Run `pytest -q`,
`hermes plugins validate .` and `hermes plugins doctor . --ci` before opening a PR.

Worked examples to learn from: [EOH](https://github.com/mojomast/EOH) ·
[Hermagotchi](https://github.com/mojomast/hermagotchi) ·
[hyperrizz](https://github.com/mojomast/hyperrizz) ·
[Hermes Strudel Studio](https://github.com/mojomast/poptart) ·
[Shortrizz](https://github.com/mojomast/hermes-shortrizz) ·
[stitchslop](https://github.com/mojomast/hermes-stitchslop) ·
[TempleOS](https://github.com/mojomast/hermes-templeos) ·
[photo-to-part](https://github.com/mojomast/hermes-photo-to-part) ·
[comfyrizz-hermes](https://github.com/mojomast/comfyrizz-hermes)

## License

[MIT](LICENSE)

## Catalog security preflight (v0.3.0)

`hpd_check` looks for SDK/auth anti-patterns (including absolute URLs to
`authedFetch` and `postMessage(..., '*')`), credential access, unsafe process
environments, private imports, profile paths, insecure URLs, wildcard binds,
`null`/`file://` origin allowlists, and handlers that return dictionaries
instead of JSON strings. Network fetches and complex data flows produce
manual-review warnings, not a security guarantee. See the bundled
[security-boundaries](skills/hermes-plugin-development/references/security-boundaries.md)
and [catalog-review-lessons](skills/hermes-plugin-development/references/catalog-review-lessons.md)
references for SSRF, file confinement, honest online clients, capture relay
budgets, pane-only privileged actions, untrusted feed text, and live-host
acceptance. Tool results use JSON strings as required by Hermes.
