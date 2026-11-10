# Worked examples (public repos)

Study these for real-world patterns. Check each repo's current state; they evolve.

| Repo | What to look at |
|---|---|
| https://github.com/mojomast/EOH | Big dashboard/desktop pane (3D globe) driven by 11 composable tools (~70 → 11); `pre_llm_call` context line; user-disabled layers; public-only fetches; later review: do not "trust" feed text in the system prompt |
| https://github.com/mojomast/gods-eye-view | Upstream standalone web app EOH is built on (non-plugin) |
| https://github.com/mojomast/hermagotchi | 8 composable tools + native pane; network/autonomy off by default; pane-only pairing approve/revoke (`unsupported_online`); no absolute URLs to `authedFetch`; the `sudo_usage` false positive |
| https://github.com/mojomast/poptart | Plugin in a subfolder (`integration/hermes`, catalog `subdir`); one lean tool; loopback Node sidecar; evaluated code only in sandboxed frames; AGPL licensing notes; clean-clone catalog install |
| https://github.com/mojomast/hyperrizz | Desktop film studio; confined paths; token-gated loopback relay; disclose write-then-execute of project scripts; hero frame at t=0 so thumbnails are not blank |
| https://github.com/mojomast/hermes-stitchslop | Four tools, live pane, driven browser. Review blockers: token on every viewer route, no wildcard bind, allowlisted `nav` origins, pane/hand-only pairing tokens |
| https://github.com/mojomast/hermes-templeos | Shared-screen Desktop pane (Watch / Shared / Take control); background frame cache so polling does not starve the gateway; React hooks from `react`; SHA-256 ISO pins; child hypervisor disclosure; companion with a hide toggle |
| https://github.com/mojomast/hermes-shortrizz | CLI + plugin; secret-scope + minimal child env + path confinement; SHA-256 pins for models; Shortrizz Studio pane as a human review gate before render; hero frame on shorts |
| https://github.com/mojomast/hermes-photo-to-part | `pre_tool_call` approval before running a model-named script; write confinement; hooks scoped to the plugin checkout; plugin in a `plugin/` subdir so evals stay out of the install |
| https://github.com/mojomast/comfyrizz-hermes | Portable Agent Plugin (`plugin.json` + skills + MCP) as an alternative to a native plugin |

Upstream catalog entries for listed plugins live in `plugin-catalog/*.yaml` in
NousResearch/hermes-agent; reading a few dozen is the fastest way to learn the house style.
