"""Fake-host tests for hermes-plugin-dev. No Hermes, no network."""
from __future__ import annotations

import importlib.util
import sys
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class FakeCtx:
    def __init__(self):
        self.tools, self.skills = {}, {}

    def register_tool(self, name, toolset, schema, handler, check_fn=None, requires_env=None,
                      is_async=False, description="", emoji="", override=False):
        assert name not in self.tools
        def decoded(args):
            result = handler(args)
            assert isinstance(result, str)
            return json.loads(result)
        self.tools[name] = (schema, decoded)

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
        result = hpd_core.check_catalog(entry)
        # The prepared entry may use the placeholder sha until an authorized
        # tag exists. Every other catalog rule must still pass.
        leftover = [e for e in result["errors"] if "placeholder" not in e]
        assert leftover == [], leftover
        assert result.get("warnings") is not None


def test_catalog_rejects_more_than_six_screenshots(tmp_path):
    sys.path.insert(0, str(ROOT))
    import hpd_core
    entry = tmp_path / "e.yaml"
    shots = "\n".join(
        f'  - https://raw.githubusercontent.com/acme/p/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/{i}.png'
        for i in range(7)
    )
    entry.write_text(
        "name: demo\n"
        "repo: https://github.com/acme/p\n"
        'sha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n'
        "category: tools\n"
        "tier: community\n"
        "version: \"0.1.0\"\n"
        "screenshots:\n" + shots + "\n"
    )
    out = hpd_core.check_catalog(entry)
    assert not out["ok"]
    assert any("6 screenshot" in e for e in out["errors"])


def test_core_override_is_refused(tmp_path):
    ctx = load()
    p = tmp_path / "patcher"
    ctx.tools["hpd_scaffold"][1]({"target_dir": str(p), "name": "patcher"})
    (p / "shim.py").write_text(
        "import hermes_cli.plugins as hp\n"
        "hp.PluginContext.register_tool = lambda *a, **k: None\n", encoding="utf-8")
    out = ctx.tools["hpd_check"][1]({"path": str(p)})
    assert not out["ok"]
    assert any("core_override" in e for e in out["core_override"]["errors"])
    (p / "shim.py").unlink()

    (p / "shim.py").write_text(
        "import sys\n"
        "sys.modules['hermes_cli.plugins'] = object()\n", encoding="utf-8")
    assert not ctx.tools["hpd_check"][1]({"path": str(p)})["ok"]


def test_core_override_allows_own_modules(tmp_path):
    ctx = load()
    p = tmp_path / "clean"
    ctx.tools["hpd_scaffold"][1]({"target_dir": str(p), "name": "clean"})
    (p / "settings.py").write_text("class C:\n    pass\n\n\nC.value = 1\n", encoding="utf-8")
    out = ctx.tools["hpd_check"][1]({"path": str(p)})
    assert out["ok"], out
    assert "core_override" not in out


def test_manifest_unknown_field_and_bad_capability(tmp_path):
    ctx = load()
    p = tmp_path / "caps"
    ctx.tools["hpd_scaffold"][1]({"target_dir": str(p), "name": "caps"})
    mf = p / "plugin.yaml"
    mf.write_text(mf.read_text().replace(
        "provides_hooks: []",
        "provides_hooks: []\nprovides_middleware: []\ncapabilities: [tools.override, typo.thing]"),
        encoding="utf-8")
    out = ctx.tools["hpd_check"][1]({"path": str(p)})
    warnings = out["manifest"]["warnings"]
    assert any("provides_middleware" in w and "catalog" in w for w in warnings)
    assert any("typo.thing" in w for w in warnings)


def test_private_imports_result_shape():
    import hpd_core
    res = hpd_core.check_private_imports(ROOT)
    assert res["ok"] is True
    assert isinstance(res["warnings"], list)
    assert set(res) >= {"checked", "warnings"}
