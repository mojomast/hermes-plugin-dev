"""Core logic for hermes-plugin-dev tools. Offline only: no network, no subprocesses."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "skills" / "hermes-plugin-development" / "templates" / "hello-hermes"
CATALOG_TEMPLATE = ROOT / "skills" / "hermes-plugin-development" / "templates" / "catalog"

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CATEGORIES = {"desktop", "memory", "platform", "web", "tools", "voice", "automation", "models", "general"}
IMAGE_HOSTS = re.compile(r"^https://(raw\.githubusercontent\.com|github\.com|[a-z0-9-]+\.githubusercontent\.com)/")
SKIP = {"__pycache__", ".pytest_cache"}


def _err(code: str, error: str, fix: str) -> dict:
    return {"ok": False, "code": code, "error": error, "fix": fix}


# ---------------------------------------------------------------- scaffold
def scaffold(target_dir: str, name: str, with_catalog: bool = True) -> dict:
    if not name or not NAME_RE.match(name):
        return _err("bad_name", f"invalid plugin name {name!r}", "Use lowercase [a-z0-9_-], max 64 chars, e.g. my-plugin.")
    if not target_dir:
        return _err("no_target", "target_dir is required", "Pass an absolute path for the new plugin folder.")
    target = Path(target_dir).expanduser().resolve()
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        return _err("target_not_empty", f"{target} exists and is not empty", "Pick a new or empty directory; nothing is overwritten.")
    tool = name.replace("-", "_")
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for src in sorted(TEMPLATE.rglob("*")):
        rel = src.relative_to(TEMPLATE)
        if any(part in SKIP for part in rel.parts) or src.is_dir():
            continue
        rel_str = str(rel).replace("hello-hermes", name)
        dst = (target / rel_str).resolve()
        if target not in dst.parents:
            return _err("path_escape", f"refusing to write outside {target}", "Report this as a bug.")
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copyfile(src, dst)
        else:
            text = text.replace("hello_hermes", tool).replace("hello-hermes", name)
            text = text.replace("Hello Hermes", name.replace("-", " ").title())
            dst.write_text(text, encoding="utf-8")
        written.append(rel_str)
    if with_catalog:
        for f in ("plugin-catalog-entry.yaml", "PR_BODY.md"):
            text = (CATALOG_TEMPLATE / f).read_text(encoding="utf-8")
            text = text.replace("hello_hermes", tool).replace("hello-hermes", name)
            text = text.replace("Hello Hermes", name.replace("-", " ").title())
            out = target / "catalog" / (f"{name}.yaml" if f.endswith(".yaml") else f)
            out.parent.mkdir(exist_ok=True)
            out.write_text(text, encoding="utf-8")
            written.append(str(out.relative_to(target)))
    return {
        "ok": True, "path": str(target), "tool": tool, "files": written,
        "next": [f"cd {target} && pytest -q", "hermes plugins doctor . --ci",
                 "hermes plugins validate . --install-deps"],
    }


# ---------------------------------------------------------------- checks
def _strict_yaml(path: Path) -> tuple[Any, list[str]]:
    import yaml

    problems: list[str] = []

    class Strict(yaml.SafeLoader):
        pass

    def construct(loader, node, deep=False):
        keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
        for k in {k for k in keys if keys.count(k) > 1}:
            problems.append(f"duplicate key {k!r} (YAML keeps the last one silently)")
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=Strict)
    except Exception as exc:  # noqa: BLE001
        return None, [f"YAML parse error: {exc}"]
    return data, problems


def check_manifest(plugin: Path) -> dict:
    mf = plugin / "plugin.yaml"
    if not mf.is_file():
        return {"ok": False, "errors": ["no plugin.yaml"], "warnings": []}
    data, errors = _strict_yaml(mf)
    warnings: list[str] = []
    if not isinstance(data, dict):
        return {"ok": False, "errors": errors or ["plugin.yaml is not a mapping"], "warnings": []}
    name = data.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        errors.append("name must match [a-z0-9_-]{1,64}")
    if not isinstance(data.get("version"), str):
        errors.append("version must be a quoted string")
    if not (plugin / "__init__.py").is_file() and not (plugin / "desktop" / "plugin.js").is_file():
        errors.append("nothing loadable: add __init__.py with register(ctx)")
    tools = data.get("provides_tools") or []
    if len(tools) != len(set(tools)):
        errors.append("provides_tools has duplicates")
    for env in data.get("requires_env") or []:
        n = env.get("name") if isinstance(env, dict) else env
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", str(n)):
            errors.append(f"requires_env {n!r} must be UPPER_SNAKE")
    rh = data.get("requires_hermes")
    if rh and not re.fullmatch(r">=\s*\d+\.\d+(\.\d+)?", str(rh)):
        warnings.append("requires_hermes should be a SemVer floor like '>=0.21.6'")
    if data.get("manifest_version") != 2:
        warnings.append("consider manifest_version: 2")
    if not (plugin / "pyproject.toml").is_file() and data.get("python_dependencies"):
        for dep in data["python_dependencies"]:
            if "<" not in str(dep):
                warnings.append(f"dependency {dep!r} has no upper bound")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "declared_tools": tools}


def check_catalog(entry: Path) -> dict:
    data, errors = _strict_yaml(entry)
    warnings: list[str] = []
    if not isinstance(data, dict):
        return {"ok": False, "errors": errors or ["not a mapping"], "warnings": []}
    raw = entry.read_text(encoding="utf-8")
    sha = data.get("sha")
    if not isinstance(sha, str):
        errors.append("sha must be a quoted 40-hex string (unquoted all-digit SHAs parse as numbers)")
    elif not SHA_RE.match(sha):
        errors.append("sha must be exactly 40 lowercase hex characters")
    elif sha == "0" * 40:
        errors.append("sha is still the placeholder; pin the release commit")
    if not str(data.get("repo", "")).startswith("https://"):
        errors.append("repo must be an https:// URL")
    if not NAME_RE.match(str(data.get("name", ""))):
        errors.append("name must match [a-z0-9_-]{1,64}")
    if data.get("category", "desktop") not in CATEGORIES:
        errors.append(f"category must be one of {sorted(CATEGORIES)}")
    if data.get("tier", "community") != "community":
        warnings.append("contributors should use tier: community")
    sub = str(data.get("subdir") or "")
    if sub and (sub.startswith("/") or "\\" in sub or any(p in ("", ".", "..") for p in sub.split("/"))):
        errors.append("subdir must be a plain relative path")
    if "version" in data and not isinstance(data["version"], str):
        errors.append("version must be quoted")
    images = ([data["image"]] if data.get("image") else []) + list(data.get("screenshots") or [])
    if len(data.get("screenshots") or []) > 6:
        errors.append("at most 6 screenshots")
    for url in images:
        if not IMAGE_HOSTS.match(str(url)):
            errors.append(f"image not on a GitHub host: {url}")
        elif isinstance(sha, str) and sha not in str(url):
            warnings.append(f"image not pinned to the entry sha: {url}")
    if images:
        warnings.append("offline lint cannot check HTTP 200; curl each image URL")
    del raw
    return {"ok": not errors, "errors": errors, "warnings": warnings}


class _FakeCtx:
    def __init__(self):
        self.tools: dict[str, dict] = {}
        self.hooks: list[str] = []
        self.skills: list[str] = []

    def register_tool(self, name, toolset, schema, handler, check_fn=None, requires_env=None,
                      is_async=False, description="", emoji="", override=False):
        self.tools[name] = schema

    def register_skill(self, name, path, description="", frontmatter=None):
        self.skills.append(name)

    def register_hook(self, hook_name, callback, *, hold_stream=False):
        self.hooks.append(hook_name)

    def __getattr__(self, item):  # other registrations are accepted and ignored
        return lambda *a, **k: None


def measure_schemas(plugin: Path) -> dict:
    init = plugin / "__init__.py"
    if not init.is_file():
        return {"ok": False, "errors": ["no __init__.py"]}
    mod_name = f"_hpd_probe_{uuid.uuid4().hex[:8]}"
    spec = importlib.util.spec_from_file_location(mod_name, init, submodule_search_locations=[str(plugin)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    ctx = _FakeCtx()
    try:
        spec.loader.exec_module(mod)
        mod.register(ctx)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "errors": [f"register(ctx) raised {type(exc).__name__}: {exc}"],
                "fix": "A register() exception leaves the plugin with 0 tools in Hermes."}
    finally:
        for k in [k for k in sys.modules if k == mod_name or k.startswith(mod_name + ".")]:
            sys.modules.pop(k, None)
    text = json.dumps(list(ctx.tools.values()), separators=(",", ":"), ensure_ascii=False)
    try:
        import tiktoken

        tokens, method = len(tiktoken.get_encoding("o200k_base").encode(text)), "o200k_base"
    except Exception:  # noqa: BLE001
        tokens, method = round(len(text) / 4), "approx(chars/4)"
    return {"ok": True, "tools": sorted(ctx.tools), "hooks": ctx.hooks, "skills": ctx.skills,
            "schema_tokens": tokens, "method": method}


def check_security(plugin: Path) -> dict:
    """Non-executing heuristic preflight, not a sandbox or a security proof.

    Findings deliberately omit source lines/values (they may contain secrets).
    Only shipped runtime source is scanned, not tests/docs/template examples.
    """
    import ast
    import ipaddress
    from urllib.parse import urlsplit

    errors, warnings = [], []
    manifest, _ = _strict_yaml(plugin / 'plugin.yaml') if (plugin / 'plugin.yaml').is_file() else ({}, [])
    floor = str((manifest or {}).get('requires_hermes', '')) if isinstance(manifest, dict) else ''
    floor_match = re.fullmatch(r'>=\s*(\d+)\.(\d+)(?:\.(\d+))?', floor)
    desktop_rest = False
    excluded = {'.git', '.venv', 'venv', 'node_modules', 'tests', 'docs',
                'references', 'templates', 'examples', '__pycache__'}

    def finding(target, path, line, rule):
        message = f"{path.relative_to(plugin)}:{line}: {rule}"
        if message not in target:
            target.append(message)

    for path in sorted(plugin.rglob('*')):
        if any(p in excluded for p in path.relative_to(plugin).parts) or path.is_symlink():
            continue
        if not path.is_file() or path.suffix not in {'.py', '.js', '.mjs', '.jsx', '.ts', '.tsx', '.html'}:
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        ui = any(p in {'dashboard', 'desktop'} for p in path.relative_to(plugin).parts)
        if 'desktop' in path.relative_to(plugin).parts and re.search(r'ctx\.rest\s*\(', text):
            desktop_rest = True
        for line, source in enumerate(text.splitlines(), 1):
            if ui:
                patterns = [
                    (r'(?:https?:)?//(?:esm\.sh|unpkg\.com|cdn\.jsdelivr\.net)|(?:import\s.*from\s*[\'\"]https?://|<script[^>]+src=[\'\"]https?://)', 'remote_pane_code: use committed bundles and SDK.React'),
                    (r'__HERMES_SESSION_TOKEN__|hermes\.webapp\.session|(?:localStorage|sessionStorage).*?(?:token|grant|session)', 'pane_token_read: use SDK auth transport'),
                    (r'(?:window|globalThis)\.fetch\s*=', 'fetch_patch: do not replace host fetch'),
                ]
                for pattern, rule in patterns:
                    if re.search(pattern, source, re.I):
                        finding(errors, path, line, rule)
                if re.search(r'authedFetch\s*\(\s*[\'\"]https?:', source):
                    finding(errors, path, line, 'authed_fetch_absolute: pass only relative plugin routes to authedFetch, never absolute http(s) URLs')
                elif re.search(r'authedFetch\s*\(', source) and not re.search(r'authedFetch\s*\(\s*[\'\"](?:/|data:|blob:)', source):
                    finding(warnings, path, line, 'authed_fetch_url: pass only relative plugin routes to authedFetch, never absolute http(s) URLs')
                if re.search(r'postMessage\s*\([^\n;]*[\'\"]\*[\'\"]', source):
                    finding(warnings, path, line, 'postmessage_wildcard: pin the target origin; do not broadcast with *')
            if re.search(r'[\'\"]0\.0\.0\.0[\'\"]', source) or re.search(r'\bbind\([^\n;]*0\.0\.0\.0|\blisten\([^\n;]*0\.0\.0\.0', source):
                finding(warnings, path, line, 'wildcard_bind: refuse 0.0.0.0 / public binds by default; loopback only, tailnet as explicit opt-in')
            # Build the pattern from parts so this file does not trip the rule.
            cors_names = "ALLOW" + "(?:ED)?_ORIGIN" + "S?"
            cors_bad = r"(?:['\"]null['\"]|file" + ":)"
            if re.search(cors_names + r".{0,80}" + cors_bad, source, re.I) or re.search(
                r"Access-Control-Allow-Origin.{0,80}" + cors_bad, source, re.I
            ):
                finding(warnings, path, line, 'cors_null_origin: drop null and file:// from origin allowlists')
            if re.search(r'~[/]\.hermes', source) or re.search(r'Path\.home\(\)\s*/\s*[\'\"]\.hermes', source):
                finding(errors, path, line, 'profile_path: use get_hermes_home()')
            for url in re.findall(r'http://[^\s\'\"<>`]+', source):
                try:
                    host = urlsplit(url.rstrip('),;')).hostname
                    if not host:
                        continue
                except ValueError:
                    continue  # not a URL literal (e.g. a regex defining this check)
                try:
                    loopback = host == 'localhost' or ipaddress.ip_address(host).is_loopback
                except ValueError:
                    loopback = False
                if not loopback:
                    finding(warnings, path, line, 'insecure_http: require HTTPS except explicit loopback development; review public research exceptions')
        if path.suffix != '.py':
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            finding(errors, path, 1, 'python_syntax: cannot inspect runtime source')
            continue
        aliases = {}
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    aliases[item.asname or item.name] = item.name
            elif isinstance(node, ast.ImportFrom):
                for item in node.names:
                    aliases[item.asname or item.name] = f'{node.module}.{item.name}'

        def name(node):
            if isinstance(node, ast.Name):
                return aliases.get(node.id, node.id)
            if isinstance(node, ast.Attribute):
                return name(node.value) + '.' + node.attr
            return ''

        handlers = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [i.name for i in node.names] if isinstance(node, ast.Import) else [node.module or '']
                if 'fcntl' in names:
                    ancestor = parents.get(node)
                    guarded = False
                    while ancestor is not None:
                        if isinstance(ancestor, ast.Try) and any(h.type is None or (isinstance(h.type, ast.Name) and h.type.id in {'ImportError', 'ModuleNotFoundError'}) for h in ancestor.handlers):
                            guarded = True
                        ancestor = parents.get(ancestor)
                    if not guarded:
                        finding(warnings, path, node.lineno, 'platform_import: guard fcntl or restrict supported platforms')
                if any(n == 'tools.desktop_ui' or n.startswith('tools.desktop_ui.') for n in names) or (isinstance(node, ast.ImportFrom) and node.module == 'tools' and any(i.name == 'desktop_ui' for i in node.names)):
                    finding(errors, path, node.lineno, 'private_host_import: use documented ctx/SDK APIs')
            if isinstance(node, ast.Subscript) and name(node.value) == 'os.environ':
                key = node.slice
            elif isinstance(node, ast.Call) and name(node.func) in {'os.getenv', 'os.environ.get'}:
                key = node.args[0] if node.args else None
            else:
                key = None
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                if re.search(r'(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)', key.value, re.I):
                    finding(errors, path, node.lineno, 'credential_env: declare requires_env and use agent.secret_scope.get_secret')
                elif key.value == 'HERMES_HOME':
                    finding(errors, path, node.lineno, 'profile_env: use get_hermes_home()')
            if not isinstance(node, ast.Call):
                continue
            fn = name(node.func)
            if fn.endswith('register_tool') or fn.endswith('_register_tool_compat'):
                for kw in node.keywords:
                    if kw.arg == 'handler' and isinstance(kw.value, ast.Name):
                        handlers.add(kw.value.id)
            if fn == 'agent.secret_scope.get_secret' and node.args and isinstance(node.args[0], ast.Constant):
                declared_env = (manifest or {}).get('requires_env', []) if isinstance(manifest, dict) else []
                declared_names = {e.get('name') if isinstance(e, dict) else e for e in declared_env}
                if node.args[0].value not in declared_names:
                    finding(warnings, path, node.lineno, 'secret_declaration: ensure get_secret name/aliases are declared in requires_env')
            if fn in {'subprocess.run', 'subprocess.Popen', 'subprocess.call', 'subprocess.check_call', 'subprocess.check_output', 'asyncio.create_subprocess_exec', 'asyncio.create_subprocess_shell'}:
                env = next((kw.value for kw in node.keywords if kw.arg == 'env'), None)
                if env is None or isinstance(env, ast.Constant) and env.value is None:
                    finding(warnings, path, node.lineno, 'child_env_inherited: pass an explicit minimal environment')
                elif any(name(n) == 'os.environ' for n in ast.walk(env)):
                    finding(errors, path, node.lineno, 'child_env_full: use an exact-name minimal allowlist, not os.environ/copy')
                else:
                    finding(warnings, path, node.lineno, 'child_env_review: verify exact-name allowlist and scoped app keys')
            if fn in {'requests.get', 'requests.post', 'requests.request', 'httpx.get', 'httpx.post', 'urllib.request.urlopen', 'urllib.request.Request'} or fn.endswith(('.session.get', '.session.request')):
                finding(warnings, path, node.lineno, 'url_fetch_review: trace untrusted URLs through DNS-pinned SSRF guard and redirects')
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (node.name in handlers or node.name in {'_handler', '_check', '_scaffold'}):
                returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
                if any(isinstance(n.value, ast.Dict) for n in returns):
                    finding(errors, path, node.lineno, 'tool_dict_result: registered handlers must return json.dumps strings')
                elif not any(isinstance(n, ast.Call) and name(n.func) == 'json.dumps' for n in ast.walk(node)):
                    finding(warnings, path, node.lineno, 'tool_result_review: verify all result/error paths serialize JSON strings')
    if desktop_rest and (not floor_match or tuple(int(v or 0) for v in floor_match.groups()) < (0, 23, 0)):
        errors.append('plugin.yaml:1: desktop_rest_floor: ctx.rest requires Hermes >=0.23.0')
    return {'ok': not errors, 'errors': errors, 'warnings': warnings,
            'scope': 'heuristic runtime source scan; manual review and live tests required'}


def check(path: str, catalog_entry: str = "", tokens: bool = True) -> dict:
    if not path:
        return _err("no_path", "path is required", "Pass the plugin directory.")
    plugin = Path(path).expanduser().resolve()
    if not plugin.is_dir():
        return _err("not_dir", f"{plugin} is not a directory", "Pass the plugin directory.")
    out: dict[str, Any] = {"manifest": check_manifest(plugin), "security": check_security(plugin)}
    if tokens:
        out["schemas"] = measure_schemas(plugin)
        declared = sorted(out["manifest"].get("declared_tools") or [])
        if out["schemas"].get("ok") and declared != out["schemas"]["tools"]:
            out["manifest"]["errors"].append(
                f"provides_tools {declared} != registered {out['schemas']['tools']}")
            out["manifest"]["ok"] = False
    if catalog_entry:
        entry = Path(catalog_entry).expanduser()
        if not entry.is_absolute():
            entry = plugin / entry
        out["catalog"] = check_catalog(entry) if entry.is_file() else {"ok": False, "errors": [f"{entry} not found"]}
    out["ok"] = all(v.get("ok", True) for v in out.values() if isinstance(v, dict))
    out["next"] = "Then run: hermes plugins doctor <path> --ci && hermes plugins validate <path> --install-deps"
    return out
