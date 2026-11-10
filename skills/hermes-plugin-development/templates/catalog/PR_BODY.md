## plugin-catalog: add <Plugin Title> v<X.Y.Z>

Adds `plugin-catalog/<name>.yaml` (YAML-only diff).

- **Repo:** https://github.com/<owner>/<repo>
- **Pinned SHA:** `<40-hex sha>` (tag `v<X.Y.Z>`, release: https://github.com/<owner>/<repo>/releases/tag/v<X.Y.Z>)
- **Subdir:** `<subdir or none>`
- **Maintainer:** @<owner> (owner of the plugin repo)

### What it does
<2-4 sentences.>

### Capabilities (match the pin)
- Tools (<N>): `<tool_a>`, `<tool_b>`
- Hooks: none
- Env / secrets: none (or: declared `requires_env`, read via `agent.secret_scope.get_secret`)

### Disclosure
<Network calls, subprocesses/sidecars, background work, files written, credential use, write-then-execute, child hypervisor / driven browser if any. "None" if none.>

### Checks run at the pinned SHA
- [ ] `python scripts/validate_plugin_catalog.py plugin-catalog/<name>.yaml` passes
- [ ] `hermes plugins validate <checkout>[/<subdir>] --install-deps` passes (note any scanner cautions and why they are benign)
- [ ] `hermes plugins doctor <checkout> --ci` passes
- [ ] Schema token cost measured with tiktoken `o200k_base` (N tools, M tokens)
- [ ] At most 6 screenshots; all image/screenshot URLs return HTTP 200 and are pinned to the same SHA; shot in Hermes dark mode
- [ ] Secret scan clean
- [ ] Real catalog install in a scratch `HERMES_HOME`: installed sha equals the pin, every declared tool registers
- [ ] Live pane (if any) connected to the right session; privileged ops are pane-only or approval-gated
- Tested on Hermes v<version>

### If this is a re-pin after review
Point-by-point map of each finding to the changed files/commits and tests.
Old sha: `<old>`. New sha: `<new>`.
