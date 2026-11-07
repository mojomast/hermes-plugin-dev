# Worked examples (public repos)

Study these for real-world patterns. Check each repo's current state; they evolve.

| Repo | What to look at |
|---|---|
| https://github.com/mojomast/EOH | Big dashboard/desktop pane (3D globe) driven by composable tools; ~70 → 11 tool consolidation; `pre_llm_call` context line; respecting user-disabled layers |
| https://github.com/mojomast/gods-eye-view | Upstream standalone web app EOH is built on (non-plugin) |
| https://github.com/mojomast/hermagotchi | 8 composable tools + native pane; network/autonomy off by default; large Python+JS test suites; the `sudo_usage` false positive |
| https://github.com/mojomast/poptart | Plugin in a subfolder (`integration/hermes`, catalog `subdir`); one lean tool; loopback Node sidecar; evaluated code only in sandboxed frames; AGPL licensing notes |
| https://github.com/mojomast/hermes-shortrizz | CLI + Hermes plugin sharing one core; heavy deps lazy-loaded; media pipeline tests |
| https://github.com/mojomast/comfyrizz-hermes | Portable Agent Plugin (`plugin.json` + skills + MCP) as an alternative to a native plugin |

Upstream catalog entries for listed plugins live in `plugin-catalog/*.yaml` in
NousResearch/hermes-agent; reading a few dozen is the fastest way to learn the house style.
