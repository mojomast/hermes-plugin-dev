"""Runs without Hermes installed: a fake ctx records registrations."""
from __future__ import annotations

import importlib.util
import sys
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class FakeCtx:
    def __init__(self):
        self.tools, self.skills, self.hooks = {}, {}, {}

    # Mirrors the host signature (hermes_cli/plugins_context.py) closely enough for tests.
    def register_tool(self, name, toolset, schema, handler, check_fn=None, requires_env=None,
                      is_async=False, description="", emoji="", override=False):
        assert name not in self.tools, f"duplicate tool {name}"
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler}

    def register_skill(self, name, path, description="", frontmatter=None):
        assert Path(path).is_file()
        self.skills[name] = Path(path)

    def register_hook(self, hook_name, callback, *, hold_stream=False):
        self.hooks[hook_name] = callback


def _load_plugin():
    spec = importlib.util.spec_from_file_location("hello_hermes_plugin", ROOT / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _manifest():
    return yaml.safe_load((ROOT / "plugin.yaml").read_text(encoding="utf-8"))


def test_registered_tools_match_manifest():
    ctx = FakeCtx()
    _load_plugin().register(ctx)
    assert sorted(ctx.tools) == sorted(_manifest()["provides_tools"])
    assert sorted(ctx.hooks) == sorted(_manifest().get("provides_hooks") or [])
    assert "hello-hermes" in ctx.skills


def test_handler_ops():
    ctx = FakeCtx()
    _load_plugin().register(ctx)
    raw = ctx.tools["hello_hermes"]["handler"]
    def h(args):
        result = raw(args)
        assert isinstance(result, str)
        return json.loads(result)
    assert h({"op": "greet", "name": "Ada"}) == {"ok": True, "message": "Hello, Ada!"}
    assert h({"op": "status"})["ok"] is True
    bad = h({"op": "nope"})
    assert bad["ok"] is False and bad["fix"]


def test_manifest_has_no_duplicate_keys():
    class Strict(yaml.SafeLoader):
        pass

    def construct(loader, node, deep=False):
        keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
        dupes = {k for k in keys if keys.count(k) > 1}
        assert not dupes, f"duplicate keys in plugin.yaml: {dupes}"
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct)
    data = yaml.load((ROOT / "plugin.yaml").read_text(encoding="utf-8"), Loader=Strict)
    assert isinstance(data["version"], str), "quote the version"
