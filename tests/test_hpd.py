"""Fake-host tests for hermes-plugin-dev. No Hermes, no network."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class FakeCtx:
    def __init__(self):
        self.tools, self.skills = {}, {}

    def register_tool(self, name, toolset, schema, handler, check_fn=None, requires_env=None,
                      is_async=False, description="", emoji="", override=False):
        assert name not in self.tools
        self.tools[name] = (schema, handler)

    def register_skill(self, name, path, description="", frontmatter=None):
        assert Path(path).is_file()
        self.skills[name] = path


def load():
    spec = importlib.util.spec_from_file_location("hpd_plugin_under_test", ROOT / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    ctx = FakeCtx()
    mod.register(ctx)
    return ctx


def test_registrations_match_manifest():
    ctx = load()
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    assert sorted(ctx.tools) == sorted(manifest["provides_tools"])
    assert "hermes-plugin-development" in ctx.skills


def test_skill_frontmatter_matches_dir():
    text = (ROOT / "skills/hermes-plugin-development/SKILL.md").read_text()
    front = yaml.safe_load(text.split("---")[1])
    assert front["name"] == "hermes-plugin-development"
    assert 0 < len(front["description"]) <= 1024
    assert len(text.splitlines()) < 500


def test_scaffold_then_check_roundtrip(tmp_path):
    ctx = load()
    target = tmp_path / "my-plug"
    res = ctx.tools["hpd_scaffold"][1]({"target_dir": str(target), "name": "my-plug"})
    assert res["ok"], res
    assert (target / "plugin.yaml").is_file() and (target / "catalog/my-plug.yaml").is_file()
    assert "my_plug" in (target / "__init__.py").read_text()
    out = ctx.tools["hpd_check"][1]({"path": str(target)})
    assert out["ok"], out
    assert out["schemas"]["tools"] == ["my_plug"]
    # placeholder sha must be flagged
    cat = ctx.tools["hpd_check"][1]({"path": str(target), "catalog_entry": "catalog/my-plug.yaml"})
    assert not cat["catalog"]["ok"] and any("placeholder" in e for e in cat["catalog"]["errors"])


def test_scaffold_refuses_nonempty_and_bad_name(tmp_path):
    ctx = load()
    (tmp_path / "x").mkdir(); (tmp_path / "x" / "keep.txt").write_text("hi")
    h = ctx.tools["hpd_scaffold"][1]
    assert h({"target_dir": str(tmp_path / "x"), "name": "ok"})["code"] == "target_not_empty"
    assert h({"target_dir": str(tmp_path / "y"), "name": "Bad Name"})["code"] == "bad_name"
    assert (tmp_path / "x" / "keep.txt").read_text() == "hi"


def test_check_catches_duplicate_keys_and_drift(tmp_path):
    ctx = load()
    p = tmp_path / "p"
    ctx.tools["hpd_scaffold"][1]({"target_dir": str(p), "name": "p"})
    mf = p / "plugin.yaml"
    mf.write_text(mf.read_text() + "name: p\n")
    out = ctx.tools["hpd_check"][1]({"path": str(p)})
    assert not out["manifest"]["ok"] and any("duplicate" in e for e in out["manifest"]["errors"])
    mf.write_text(mf.read_text().replace("name: p\n", "", 1).replace("  - p\n", "  - p\n  - ghost\n"))
    out = ctx.tools["hpd_check"][1]({"path": str(p)})
    assert any("ghost" in e for e in out["manifest"]["errors"])


def test_check_unquoted_sha(tmp_path):
    ctx = load()
    p = tmp_path / "q"
    ctx.tools["hpd_scaffold"][1]({"target_dir": str(p), "name": "q"})
    c = p / "catalog/q.yaml"
    c.write_text(c.read_text().replace('"0000000000000000000000000000000000000000"', "1234567890123456789012345678901234567890"))
    out = ctx.tools["hpd_check"][1]({"path": str(p), "catalog_entry": str(c)})
    assert any("quoted" in e for e in out["catalog"]["errors"])


def test_repo_catalog_entry_is_valid():
    entry = ROOT / "catalog/hermes-plugin-dev.yaml"
    if entry.is_file():
        sys.path.insert(0, str(ROOT))
        import hpd_core
        assert hpd_core.check_catalog(entry)["ok"]
