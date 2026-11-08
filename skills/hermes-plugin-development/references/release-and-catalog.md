# Release, catalog listing, deploy

## Versioning and release

1. Feature branch → tests, `doctor --ci`, `validate --install-deps` green.
2. Bump `version` in `plugin.yaml` (and `pyproject.toml`; keep them equal) with a
   strict bump script. Update CHANGELOG and README "tested with Hermes vX.Y.Z".
3. Merge to main (with the owner's approval if it isn't you).
4. `git tag vX.Y.Z <commit> && git push origin vX.Y.Z`, then create a GitHub release
   at that tag (`gh release create vX.Y.Z --notes-file ...`).
5. The tag's commit is the **full 40-hex SHA** you pin in the catalog.
6. Don't ship a self-updater (catalog rule 3). Updates come via re-pins.

## Catalog entry

Schema: `plugin-catalog/README.md` "Entry schema". Template:
`templates/catalog/plugin-catalog-entry.yaml`.

- `sha`: full 40 lowercase hex. **Quote it.** An all-digit placeholder parses as an
  int and the validator reports `sha 0 must be exactly 40 lowercase hex characters`.
- `subdir`: plain relative path (no `..`, `.`, absolute, backslashes).
- `tier: community` (only maintainers set official/verified).
- `category`: desktop | memory | platform | web | tools | voice | automation | models | general.
- `version`: quoted cosmetic label. Bump with the sha.
- `image` (2:1) and up to 6 `screenshots`: https on `raw.githubusercontent.com`,
  `github.com` or `*.githubusercontent.com`, pinned to the same sha. **Each must return
  HTTP 200**; check with `curl -sI -o /dev/null -w '%{http_code}' URL`.
- `readme: true` renders the README **at the pinned sha** on the docs site; make it good.
- `capabilities` must match what `register()` does at the pin (rule 6).

Validate structurally inside a hermes-agent checkout:

```bash
python scripts/validate_plugin_catalog.py plugin-catalog/<name>.yaml   # --json available
```

Then the behavioural gate on a clean clone at the pin:

```bash
git clone https://github.com/<owner>/<repo> /tmp/p && git -C /tmp/p checkout <sha>
hermes plugins validate /tmp/p[/<subdir>] --install-deps
```

## Opening the PR

1. Fork NousResearch/hermes-agent. Branch from up-to-date upstream `main`:
   `catalog/<name>-vX.Y.Z`.
2. Diff = one file under `plugin-catalog/`.
3. Push to your fork, open the PR against `NousResearch/hermes-agent:main`
   (`gh pr create -R NousResearch/hermes-agent --base main --head <you>:catalog/<name>-vX.Y.Z
   --title "plugin-catalog: add <Title> vX.Y.Z" --body-file PR_BODY.md`).
4. Body: `templates/catalog/PR_BODY.md` (repo, sha, release link, tools, disclosure,
   checks run, scanner cautions explained).
5. Every later SHA bump is a **new PR** (rule 4) showing old → new sha.
6. Submitter should be the plugin owner or a major contributor (rule 5).

### "CreatePullRequest" permission errors

Observed (Nov 2026): contributors without write access can have **at most 5 open PRs**
on NousResearch/hermes-agent. At the cap, PR creation fails everywhere: `gh` GraphQL
("does not have the correct permissions to execute CreatePullRequest"), REST (404),
and GitHub-App integrations ("Resource not accessible by integration"). Your auth is
fine. The web UI shows "You've reached this repository's open pull request limit".
Fix: close or land one of your open PRs, then retry, or use the compare link
`https://github.com/NousResearch/hermes-agent/compare/main...<you>:hermes-agent:<branch>?expand=1`.
(Limit observed from GitHub's error text; not documented in the hermes-agent repo.)

## Deploying to a running Hermes (yours or a test host)

1. Get the owner's OK before deploying or restarting anything.
2. Record the **rollback SHA** (`git -C <checkout> rev-parse HEAD`) and back up:
   `cp -a <checkout> ~/.hermes/backups/<name>-$(date +%Y%m%d-%H%M%S)`. Back up the plugin's
   `plugin-data/<name>/` too if a migration touches it.
3. `git fetch && git checkout <target-sha>` in the checkout that `~/.hermes/plugins/<name>`
   points to. Install deps if `pyproject.toml` changed.
4. Restart what's affected. `plugin_api.py` or route changes need a gateway/dashboard
   restart (existing routes aren't re-mounted). Tool code changes need a session or
   gateway reload, depending on how Hermes runs (systemd user units are common).
5. `hermes plugins doctor <id>` and `hermes plugins list`: check tool/hook counts,
   then exercise one real tool end to end.
6. On failure: `git checkout <rollback-sha>`, restart, re-run doctor, report.

Never merge, tag, release, or re-pin without the owner's explicit approval.


## Reviewed delta and portable install
Install only the catalog `subdir` at the exact pin into a clean temporary tree: it must be self-contained without parent-repo files or uncommitted/generated output. Commit required built UI/service/assets/guest documents and bundled skills, with reproducible source + lockfile, or ship runnable source inside that subdir. No install-time developer build assumption. Guard POSIX-only `fcntl` imports with a portable fallback, or truthfully restrict advertised platforms and test unsupported-platform behavior. Keep public INTEGRATION docs neutral: no personal hosts, account names, local deployment instructions or stale catalog claims.

After a requested repin, prepare a point-by-point review response mapping each finding to the changed files/commits and test evidence; name the old and new pin and summarize the delta. Posting a comment, merge, tag, release or catalog change needs the user's authorization: a checklist is not approval. Keep versions consistent across manifest, packaging, portable/Claude metadata and catalog labels. Never invent a self-referential catalog SHA; the catalog pin is a separate explicitly authorized operation.
