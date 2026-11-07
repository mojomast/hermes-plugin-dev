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
<Network calls, subprocesses/sidecars, background threads, files written, credential use. "None" if none.>

### Checks run at the pinned SHA
- [ ] `python scripts/validate_plugin_catalog.py plugin-catalog/<name>.yaml` passes
- [ ] `hermes plugins validate <checkout>[/<subdir>] --install-deps` passes (note any scanner cautions and why they are benign)
- [ ] `hermes plugins doctor <checkout> --ci` passes
- [ ] All image/screenshot URLs return HTTP 200 and are pinned to the same SHA
- [ ] Secret scan clean
- Tested on Hermes v<version>
