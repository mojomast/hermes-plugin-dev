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


def check(path: str, catalog_entry: str = "", tokens: bool = True) -> dict:
    if not path:
        return _err("no_path", "path is required", "Pass the plugin directory.")
    plugin = Path(path).expanduser().resolve()
    if not plugin.is_dir():
        return _err("not_dir", f"{plugin} is not a directory", "Pass the plugin directory.")
    out: dict[str, Any] = {"manifest": check_manifest(plugin)}
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
