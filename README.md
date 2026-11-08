<p align="center">
  <img src="assets/banner-v3.jpg" alt="Hermes Plugin Dev: a skill + plugin for building Hermes plugins" width="100%">
</p>

<h1 align="center">hermes-plugin-dev</h1>

<p align="center">
  <b>Teach any coding agent to ship Hermes Agent plugins that pass review the first time.</b><br>
  One Agent Skill + one Hermes plugin, distilled from shipping real community plugins.
</p>

<p align="center">
  <a href="https://github.com/mojomast/hermes-plugin-dev/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/mojomast/hermes-plugin-dev/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="https://agentskills.io"><img alt="Agent Skills" src="https://img.shields.io/badge/Agent%20Skills-compatible-8A2BE2"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img alt="Hermes Agent" src="https://img.shields.io/badge/Hermes%20Agent-%E2%89%A50.21.6-black"></a>
  <img alt="Tool schema cost" src="https://img.shields.io/badge/tool%20schemas-190%20tokens-success">
</p>

---

## Why this exists

[Hermes Agent](https://github.com/NousResearch/hermes-agent) has a powerful plugin system
and a reviewed plugin catalog. Getting a plugin from idea to listed means learning a dozen
sharp edges the hard way:

- a stray keyword to `register_tool` and your plugin silently loads with **0 tools**
- a duplicated YAML key that PyYAML quietly "fixes" for you
- an unquoted commit SHA the catalog validator reads as a number
- a dashboard API change that won't show up until you restart the gateway
- a security scan that fails your plugin because your *README* mentions a scary command word
- a PR that won't open because of a GitHub limit, not your auth

This repo captures those lessons (each **checked against hermes-agent source**, with a
[verification log](skills/hermes-plugin-development/references/verification.md)) in a
format every major coding agent can load. When installed into Hermes, it also gives the
Hermes agent two small tools to build plugins itself.

## What's inside

| | |
|---|---|
| 🧠 **Agent Skill** | [`skills/hermes-plugin-development/`](skills/hermes-plugin-development/SKILL.md): a core guide plus 11 deep-dive references (manifest, `ctx` API, all 46 hooks, capabilities & isolation, panes, testing, release & catalog, pitfalls, hackathons, worked examples, verification). |
| 🧩 **Template plugin** | [`templates/hello-hermes`](skills/hermes-plugin-development/templates/hello-hermes): a minimal plugin that passes `hermes plugins validate` and `doctor --ci` as-is, with a fake-host test, strict-YAML check, version bump script and schema-token meter. |
| 📋 **Catalog kit** | [Catalog entry](skills/hermes-plugin-development/templates/catalog/plugin-catalog-entry.yaml) and [PR body](skills/hermes-plugin-development/templates/catalog/PR_BODY.md) templates matching the upstream schema. |
| 🛠️ **Hermes plugin** | `plugin.yaml` + `register(ctx)` at the repo root: bundles the skill and adds **2 lean tools** (190 o200k tokens total). |

### The two tools

| Tool | What it does | Safety |
|---|---|---|
| `hpd_scaffold(target_dir, name)` | Creates a new plugin from the template, renamed, with a catalog entry + PR body stub | Writes only inside `target_dir`; refuses non-empty dirs; never overwrites |
| `hpd_check(path, catalog_entry?)` | Offline lint: strict YAML, manifest rules, `provides_tools` vs registered, schema token cost, catalog entry rules (sha, hosts, category, subdir) | Read-only. Token measure imports the target's `register()` with a fake host, the same as `hermes plugins doctor` |

No network calls, no subprocesses, no git, no credentials.

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
        hpd_check    → manifest ✓  tools match ✓  schema 142 tokens
        Run: hermes plugins doctor ~/code/ollama-models --ci
             hermes plugins validate ~/code/ollama-models --install-deps
```

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
├── tests/                                   # fake-host tests, no Hermes needed
└── .github/workflows/ci.yml                 # pytest + gitleaks
```

## FAQ

**Is this an official Nous Research project?** No. It's a community project. Upstream docs
and source always win; the skill says so and links them.

**Will it go stale?** Hermes moves fast. Every claim is tagged in the
[verification log](skills/hermes-plugin-development/references/verification.md) with the
Hermes version it was checked against, and unverified items are marked. PRs welcome.

**Why only two tools?** Every tool schema costs context on every turn. Two composable tools
(190 tokens) cover scaffolding and linting. Running `doctor`/`validate` stays in your
terminal, where Hermes's own checks are authoritative.

**Does it run my plugin's code?** Only `hpd_check`'s token measure, which imports your
`register()` with a fake host, like `hermes plugins doctor` does. Only check code you trust.

## Contributing

Found a new pitfall? Add it to
[`references/pitfalls.md`](skills/hermes-plugin-development/references/pitfalls.md) with the
symptom, cause and fix, and note in `verification.md` how you confirmed it. Run `pytest -q`,
`hermes plugins validate .` and `hermes plugins doctor . --ci` before opening a PR.

Worked examples to learn from: [EOH](https://github.com/mojomast/EOH) ·
[Hermagotchi](https://github.com/mojomast/hermagotchi) ·
[Hermes Strudel Studio](https://github.com/mojomast/poptart) ·
[Shortrizz](https://github.com/mojomast/hermes-shortrizz) ·
[comfyrizz-hermes](https://github.com/mojomast/comfyrizz-hermes)

## License

[MIT](LICENSE)

## What's new in 0.3.0

Brought back in line with `hermes-agent` `main` (verified @ `acdc8f1ba6`, 2026-11-08):

- **`hpd_check` now mirrors the newer admission lints** — core-override rebinds
  (`setattr`/`sys.modules`/`mock.patch` on Hermes internals) are errors, imports
  outside the generated public plugin API (`hermes_cli/data/plugin_api.json`) are
  warnings, and `plugin.yaml` gets unknown-field, `kind` and capability-id checks.
- **Two new skill references**: `hooks.md` (all 46 hook names by family, the
  observer/transform/directive/policy return shapes, timeout rules) and
  `capabilities-and-isolation.md` (the 8 consent-gated capability ids, and what
  `plugins.isolation: host` refuses to load).
- **Corrections**: `provides_middleware` is a catalog `capabilities:` key, not a
  `plugin.yaml` field (the old template logged an unknown-field warning);
  `override=True` is gated by the `tools.override` capability, not only the legacy
  `allow_tool_override` boolean.

## Catalog security preflight (v0.2.0)

Checks SDK/auth anti-patterns, credential access, unsafe process environments, private imports, profile paths, insecure URLs and direct dictionary handler returns. Network fetches and complex data flows produce manual-review warnings, not a security guarantee. See the bundled security-boundaries reference for SSRF, file confinement, honest online clients, capture relay budgets and live-host acceptance. Tool results now use JSON strings as required by Hermes.
