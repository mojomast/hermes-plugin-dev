
# Catalog security boundaries

## Untrusted URL fetches (SSRF)
Treat model arguments, pin links, OSM website tags and upstream redirect locations as untrusted. Use a centralized public-only fetch helper: allowlist schemes (HTTPS for configured online services; HTTP only for explicitly approved loopback development), reject URL credentials, malformed hosts and control characters; resolve every A/AAAA address and reject any non-global address, including private, loopback, link-local/metadata, CGNAT, multicast, reserved, unspecified and IPv4-mapped IPv6 equivalents. Pin the connection to vetted addresses while preserving TLS hostname verification/SNI: a second DNS lookup permits rebinding. Disable ambient proxies. Disable redirects or repeat validation and connection pinning at every hop with a bounded hop count. Bound time, response bytes and decoding. A scheme check alone is not SSRF protection. A documented public HTTP research exception must still use the full public-address guard; it is not a license for HTTP service credentials.

Test localhost, metadata addresses, mixed public/private DNS answers, mapped IPv6, DNS rebinding and a public-to-private redirect without actually contacting those hosts. Do not grant loopback exceptions to arbitrary user-supplied research URLs.

## Credentials, processes and files
Declare every credential (including aliases) in `requires_env`; obtain it only through `from agent.secret_scope import get_secret`. Missing host scope fails closed: never fall back to the ambient process environment, dotenv, keychains, browser storage or credential files. Remove admin `op=keys`/key-import/key-export operations. Only report configured/not-configured status, never values. Do not write secrets to process-wide environment.

Every subprocess, including Node/npm and helpers, receives an explicit minimal environment. Default inheritance (omitting `env`) is unsafe too. Use an exact-name allowlist of required non-secret settings; do not copy the whole process environment, prefix-wide `NODE_*`, or `NODE_OPTIONS`. Add only specifically required application credentials retrieved via secret scope. Test with a sentinel unrelated secret and assert it never reaches the child.

Use documented host APIs, not `tools.desktop_ui` or other private host internals. Use `hermes_constants.get_hermes_home()` and profile-aware plugin data APIs, never hardcoded `~/.hermes` or raw `HERMES_HOME` reads. Resolve paths and symlinks before checking containment under the plugin data directory; reject traversal, absolute escapes and symlink escapes for imports AND exports. An extra directory must be configured explicitly by the user/host, never granted by an LLM argument, and must not be a filesystem root. Keep state out of the installed checkout.
