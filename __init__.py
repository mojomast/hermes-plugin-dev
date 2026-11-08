"""hermes-plugin-dev: a Hermes plugin for building Hermes plugins.

Registers the bundled hermes-plugin-development skill and two lean, offline tools.
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
TOOLSET = "hermes-plugin-dev"

SCAFFOLD_SCHEMA = {
    "name": "hpd_scaffold",
    "description": "Create a new Hermes plugin from a template that passes validate/doctor. Writes only into target_dir (must be new or empty).",
    "parameters": {
        "type": "object",
        "properties": {
            "target_dir": {"type": "string", "description": "Absolute path of the new plugin folder."},
            "name": {"type": "string", "description": "Plugin id, [a-z0-9_-]."},
        },
        "required": ["target_dir", "name"],
        "additionalProperties": False,
    },
}

CHECK_SCHEMA = {
    "name": "hpd_check",
    "description": "Lint a Hermes plugin offline: strict plugin.yaml, provides_tools vs registered, security preflight, schema token cost (imports trusted register() with a fake host), optional catalog entry.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Plugin directory."},
            "catalog_entry": {"type": "string", "description": "Optional catalog YAML path."},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def _core():
    name = "hermes_plugin_dev_core"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _HERE / "hpd_core.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _scaffold(args: dict | None = None, **_kw) -> str:
    a = args or {}
    return json.dumps(_core().scaffold(str(a.get("target_dir") or ""), str(a.get("name") or "")))


def _check(args: dict | None = None, **_kw) -> str:
    a = args or {}
    return json.dumps(_core().check(str(a.get("path") or ""), str(a.get("catalog_entry") or "")))


def _register_tool_compat(register, **kwargs) -> None:
    try:
        params = inspect.signature(register).parameters
    except (TypeError, ValueError):
        params = {}
    if params and not any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        kwargs = {k: v for k, v in kwargs.items() if k in params}
    register(**kwargs)


def register(ctx) -> None:
    skills = _HERE / "skills"
    if skills.is_dir() and hasattr(ctx, "register_skill"):
        for child in sorted(p for p in skills.iterdir() if p.is_dir()):
            if (child / "SKILL.md").is_file():
                ctx.register_skill(child.name, child / "SKILL.md")
    for schema, handler in ((SCAFFOLD_SCHEMA, _scaffold), (CHECK_SCHEMA, _check)):
        _register_tool_compat(ctx.register_tool, name=schema["name"], toolset=TOOLSET,
                              schema=schema, handler=handler, description=schema["description"], emoji="🛠️")
