# Changelog

## 0.3.0 — 2026-11-10

Skill, references, and README updated with catalog-review lessons observed
between 8 and 10 Nov 2026 (America/Toronto). Version bump only: **no tag,
no GitHub release, and no catalog PR**.

- New reference: `references/catalog-review-lessons.md`. Coverage includes
  pane-only privileged actions (`unsupported_online` for pairing approve/revoke),
  untrusted feed text (never "trust" it in a system prompt), no absolute URLs
  to `SDK.authedFetch`, token-gated loopback relays (every route, Host check,
  no `0.0.0.0` default, allowlisted browser `nav`), hook scope, `pre_tool_call`
  approval, the catalog 6-screenshot cap, scratch-home install verification,
  reviewers returning after a full-tree re-read, dark-mode screenshots,
  gateway-safe frame polling, shared-pane input arbiters, SHA-256 pins for
  downloads, secret-scrubbing in tool errors, and restoring enablement after
  a test on a shared host.
- README rewritten. Banner unchanged (`assets/banner-v3.jpg`). Schema cost
  badge corrected to the measured **190** o200k tokens (was a stale 185).
- `docs/SUBMISSION.md` drafts the catalog entry and PR body for Kyle to review.
  The prepared `catalog/hermes-plugin-dev.yaml` uses a placeholder sha until
  an authorized tag exists.
- `hpd_check` security preflight: errors on absolute `http(s):` URLs passed to
  `authedFetch`; warnings for other non-relative `authedFetch` arguments,
  `postMessage(..., '*')`, wildcard `0.0.0.0` binds, and `null`/`file://`
  origin allowlists.
- Worked examples now include hyperrizz, stitchslop, TempleOS, and photo-to-part.

## 0.2.0 — 2026-11-08

Codify catalog security review lessons and preflight checks (SSRF, secret
scope, child environments, SDK auth transport, JSON-string tool results,
honest offline/online clients, capture relay budgets, live acceptance).

## 0.1.0 — 2026-11-07

Initial release: bundled hermes-plugin-development skill, `hpd_scaffold` and
`hpd_check`, hello-hermes template, catalog kit.
