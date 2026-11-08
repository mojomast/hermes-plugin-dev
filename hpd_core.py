"""Core logic for hermes-plugin-dev tools. Offline only: no network, no subprocesses."""
from __future__ import annotations

import ast
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
SCAN_EXCLUDE = {".git", ".venv", "venv", "node_modules", "tests", "docs", "references",
                "templates", "examples", "__pycache__"}

# Recognized plugin.yaml fields (`hermes_cli/plugins_manifest.py::_KNOWN_MANIFEST_FIELDS`).
# Anything else is logged as "unknown manifest field(s) ignored" on every load under v2.
KNOWN_MANIFEST_FIELDS = {
    "name", "version", "description", "author", "requires_env", "provides_tools", "provides_hooks",
    "kind", "hooks", "label", "optional_env", "platforms", "external_dependencies",
    "pip_dependencies", "provides_browser_providers", "provides_web_providers",
    "manifest_version", "api_version", "requires_plugins", "python_dependencies", "config_schema",
    "license", "homepage", "tags", "capabilities", "emits", "listens", "hermes", "depends",
    "requires_hermes", "python_runtime", "provides_locales", "requires_auth", "oauth", "config_keys",
}
VALID_KINDS = {"standalone", "backend", "exclusive", "platform", "model-provider"}
# `hermes_cli/plugin_capabilities.py::_CAPABILITY_ROWS` — unknown ids are dropped, so a typo is a
# silent downgrade rather than an error.
VALID_CAPABILITIES = {
    "tools.override", "llm.provider_override", "llm.model_override", "llm.agent_id_override",
    "llm.profile_override", "llm.task_override", "llm.side_question", "gateway.platform_actions",
}
# Fallback only: the real list is the Hermes checkout's own top-level packages/modules.
CORE_TOP_LEVEL = {
    "agent", "gateway", "hermes_cli", "hermes_platform", "hermes_state", "hermes_constants",
    "tools", "plugins", "providers", "cron", "pm", "channels", "tui_gateway", "sessions", "utils",
}


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
    unknown = sorted(set(data) - KNOWN_MANIFEST_FIELDS)
    if unknown:
        warnings.append(
            f"unknown manifest field(s) ignored by Hermes: {', '.join(unknown)}"
            + (" — provides_middleware belongs in the catalog capabilities block"
               if "provides_middleware" in unknown else ""))
    kind = data.get("kind")
    if kind is not None and kind not in VALID_KINDS:
        errors.append(f"kind {kind!r} must be one of {sorted(VALID_KINDS)}")
    caps = data.get("capabilities") or []
    if not isinstance(caps, list):
        errors.append("capabilities must be a list of capability ids")
    else:
        for cap in caps:
            if cap not in VALID_CAPABILITIES:
                warnings.append(
                    f"unknown capability id {cap!r} is dropped by Hermes (valid: "
                    f"{', '.join(sorted(VALID_CAPABILITIES))}) — the feature will be off")
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


def _scan_files(plugin: Path):
    """Runtime Python the plugin ships: no tests, docs, examples, references or templates."""
    for path in sorted(plugin.rglob("*.py")):
        rel = path.relative_to(plugin)
        if SCAN_EXCLUDE.intersection(rel.parts[:-1]):
            continue
        if rel.name.startswith("test_") or rel.name.endswith("_test.py") or rel.name == "conftest.py":
            continue
        yield path, rel


def _local_module_names(plugin: Path) -> set[str]:
    names: set[str] = set()
    for path in plugin.rglob("*"):
        rel = path.relative_to(plugin)
        if SCAN_EXCLUDE.intersection(rel.parts):
            continue
        names.add(path.stem if path.suffix == ".py" else path.name)
    return names


def _core_roots(local: set[str]) -> set[str]:
    """Hermes-owned top-level names: the checkout's packages and root modules when importable."""
    roots = set(CORE_TOP_LEVEL)
    try:
        spec = importlib.util.find_spec("hermes_cli")
    except (ImportError, ValueError):
        spec = None
    if spec is not None and spec.origin:
        root = Path(spec.origin).resolve().parent.parent
        try:
            roots |= {p.name for p in root.iterdir() if p.is_dir() and (p / "__init__.py").is_file()}
            roots |= {p.stem for p in root.glob("*.py")}
        except OSError:
            pass
    return (roots - {"setup", "conftest"}) - local


def _dotted(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _import_aliases(tree) -> dict:
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for item in node.names:
                aliases[item.asname or item.name] = f"{node.module}.{item.name}"
    return aliases


def check_core_override(plugin: Path) -> dict:
    """Static tripwire for rebinding Hermes core (`validate`'s `no core override` check).

    A plugin extends Hermes through hooks, middleware, provider profiles and SDK slots. Assigning
    over a core function, method, module attribute, `sys.modules` entry or `mock.patch` target
    collides with every other plugin patching the same seam and breaks on the next release.
    """
    _ast = ast  # module-level import; alias keeps the scanner body readable

    local = _local_module_names(plugin)
    roots = _core_roots(local)
    errors: list[str] = []

    def finding(path, line, rule):
        msg = f"{path.relative_to(plugin)}:{line}: {rule}"
        if msg not in errors:
            errors.append(msg)

    for path, _rel in _scan_files(plugin):
        try:
            tree = _ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        aliases = _import_aliases(tree)

        def is_core_name(node) -> bool:
            if not isinstance(node, _ast.Name):
                return False
            resolved = aliases.get(node.id, node.id)
            return resolved.split(".")[0] in roots

        for node in _ast.walk(tree):
            targets = []
            if isinstance(node, _ast.Assign):
                targets = node.targets
            elif isinstance(node, (_ast.AnnAssign, _ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                if isinstance(target, _ast.Attribute):
                    base = target
                    while isinstance(base, _ast.Attribute):
                        base = base.value
                    if is_core_name(base):
                        finding(path, getattr(node, "lineno", 1), f"core_override: rebinds {_dotted(target)}")
                elif (isinstance(target, _ast.Subscript) and _dotted(target.value) == "sys.modules"
                      and isinstance(target.slice, _ast.Constant) and isinstance(target.slice.value, str)
                      and target.slice.value.split(".")[0] in roots):
                    finding(path, getattr(node, "lineno", 1), f"core_override: writes sys.modules[{target.slice.value!r}]")
            if isinstance(node, _ast.Call):
                fn = _dotted(node.func).split(".")[-1]
                if fn == "setattr" and node.args and is_core_name(node.args[0]):
                    finding(path, node.lineno, f"core_override: setattr({_dotted(node.args[0])}, ...)")
                elif fn == "patch" and node.args and isinstance(node.args[0], _ast.Constant) \
                        and isinstance(node.args[0].value, str):
                    target = node.args[0].value
                    if target.split(".")[0] in roots and target.count(".") >= 2:
                        finding(path, node.lineno, f"core_override: mock.patch({target!r})")
    return {
        "ok": not errors, "errors": errors,
        "fix": "Use a hook, middleware, provider registration or the Desktop SDK slot. If no public "
               "surface reaches what you need, request the hook upstream instead of patching core.",
    }


def _public_api_entries() -> set[str] | None:
    """`hermes_cli/data/plugin_api.json` when a Hermes checkout is importable, else None."""
    try:
        spec = importlib.util.find_spec("hermes_cli")
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    data_path = Path(spec.origin).resolve().parent / "data" / "plugin_api.json"
    if not data_path.is_file():
        return None
    try:
        data = json.loads(data_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return {entry for group in data.get("groups", []) for entry in group.get("entries", [])}


def _module_covered(entries: set[str], module: str) -> bool:
    return any(":" not in entry and (module == entry or module.startswith(entry + "."))
               for entry in entries)


def _import_allowed(entries: set[str], module: str, name: str | None = None) -> bool:
    if name is None:
        return _module_covered(entries, module)
    if f"{module}:{name}" in entries:
        return True
    if _module_covered(entries, f"{module}.{name}"):
        return True
    return _module_covered(entries, module) and not name.startswith("_")


def _is_type_checking(test) -> bool:
    return ((isinstance(test, ast.Name) and test.id == "TYPE_CHECKING")
            or (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"))


def _type_checking_walk(node, in_tc: bool = False):
    """Yield import nodes that are not inside an `if TYPE_CHECKING:` block."""
    for child in ast.iter_child_nodes(node):
        child_tc = in_tc or (isinstance(child, ast.If) and _is_type_checking(child.test))
        if not child_tc and isinstance(child, (ast.Import, ast.ImportFrom)):
            yield child
        yield from _type_checking_walk(child, child_tc)


def check_private_imports(plugin: Path) -> dict:
    """Warn on imports outside the published plugin API (catalog rule 9; `validate` warns too)."""
    entries = _public_api_entries()
    if entries is None:
        return {"ok": True, "checked": False, "warnings": [],
                "note": "public API list unavailable offline (Hermes >= 0.23 importable, or accept "
                        "`hermes plugins validate` as the authoritative warning)"}

    local = _local_module_names(plugin)
    roots = _core_roots(local)
    warnings: list[str] = []
    for path, _rel in _scan_files(plugin):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in _type_checking_walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.split(".")[0] in local or item.name.split(".")[0] not in roots:
                        continue
                    if not _import_allowed(entries, item.name):
                        msg = f"{path.relative_to(plugin)}:{node.lineno}: private_import: {item.name} is not in the public plugin API"
                        if msg not in warnings:
                            warnings.append(msg)
            else:
                if node.level or not node.module or node.module.split(".")[0] in local:
                    continue
                if node.module.split(".")[0] not in roots:
                    continue
                for item in node.names:
                    if item.name == "*":
                        continue
                    if not _import_allowed(entries, node.module, item.name):
                        msg = (f"{path.relative_to(plugin)}:{node.lineno}: private_import: "
                               f"{node.module}.{item.name} is not in the public plugin API")
                        if msg not in warnings:
                            warnings.append(msg)
    return {
        "ok": True, "checked": True, "warnings": warnings[:20],
        "total": len(warnings),
        "fix": "Import from the modules/names listed in developer-guide/plugins/public-api.md; "
               "internal paths move between releases and break the plugin.",
    }


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

    core = check_core_override(plugin)
    if not core["ok"]:
        out["core_override"] = core
    imports = check_private_imports(plugin)
    if imports.get("warnings") or not imports.get("checked"):
        out["private_imports"] = imports

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
