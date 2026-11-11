"""hpd_check must not import or execute the target plugin. CLI --execute may."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import hpd_core  # noqa: E402
from test_hpd import load  # noqa: E402


MALICIOUS_INIT = '''
from pathlib import Path
_HERE = Path(__file__).resolve().parent
(_HERE / "EXECUTED").write_text("module-level", encoding="utf-8")

def register(ctx):
    (_HERE / "REGISTERED").write_text("register", encoding="utf-8")
    ctx.register_tool(
        name="boom",
        toolset="boom",
        schema={
            "name": "boom",
            "description": "should be visible to static parse only",
            "parameters": {"type": "object", "properties": {}},
        },
        handler=lambda args: None,
    )
'''

PLUGIN_YAML = '''\
name: boom
version: "0.1.0"
description: fixture
provides_tools:
  - boom
provides_hooks: []
'''


def _malicious(tmp_path: Path) -> Path:
    plugin = tmp_path / "boom"
    plugin.mkdir()
    (plugin / "plugin.yaml").write_text(PLUGIN_YAML, encoding="utf-8")
    (plugin / "__init__.py").write_text(MALICIOUS_INIT, encoding="utf-8")
    return plugin


def test_hpd_check_tool_does_not_execute_target(tmp_path):
    plugin = _malicious(tmp_path)
    ctx = load()
    out = ctx.tools["hpd_check"][1]({"path": str(plugin)})
    assert not (plugin / "EXECUTED").exists()
    assert not (plugin / "REGISTERED").exists()
    assert out["schemas"]["source"] == "static"
    assert out["schemas"]["tools"] == ["boom"]
    assert "schemas_executed" not in out


def test_hpd_check_ignores_execute_flag_from_model(tmp_path):
    plugin = _malicious(tmp_path)
    ctx = load()
    out = ctx.tools["hpd_check"][1]({"path": str(plugin), "execute": True, "tokens": True})
    assert not (plugin / "EXECUTED").exists()
    assert not (plugin / "REGISTERED").exists()
    assert "schemas_executed" not in out


def test_tool_path_never_calls_measure_schemas(tmp_path, monkeypatch):
    plugin = _malicious(tmp_path)
    ctx = load()

    def boom(*_a, **_k):
        raise AssertionError("import-based measure_schemas ran on the tool path")

    monkeypatch.setattr(hpd_core, "measure_schemas", boom)
    monkeypatch.setattr(sys.modules["hermes_plugin_dev_core"], "measure_schemas", boom)
    out = ctx.tools["hpd_check"][1]({"path": str(plugin)})
    assert out["schemas"]["source"] == "static"
    assert not (plugin / "EXECUTED").exists()


def test_static_tokens_match_executed_for_this_plugin_and_template(tmp_path):
    static = hpd_core.measure_schemas_static(ROOT)
    executed = hpd_core.measure_schemas(ROOT)
    assert static["ok"] and executed["ok"]
    assert static["tools"] == executed["tools"]
    assert static["schema_tokens"] == executed["schema_tokens"]
    assert static["calls"] == static["resolved"] == 2

    ctx = load()
    target = tmp_path / "my-plug"
    assert ctx.tools["hpd_scaffold"][1]({"target_dir": str(target), "name": "my-plug"})["ok"]
    static = hpd_core.measure_schemas_static(target)
    executed = hpd_core.measure_schemas(target)
    assert static["tools"] == executed["tools"] == ["my_plug"]
    assert static["schema_tokens"] == executed["schema_tokens"]
    assert static["calls"] == static["resolved"] == 1
    assert not any(
        (target / name).exists() for name in ("EXECUTED", "REGISTERED")
    )


def test_cli_default_is_static(tmp_path):
    plugin = _malicious(tmp_path)
    import hpd_cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = hpd_cli.main(["check", str(plugin)])
    assert code == 0
    out = json.loads(buf.getvalue())
    assert out["schemas"]["source"] == "static"
    assert "schemas_executed" not in out
    assert not (plugin / "EXECUTED").exists()
    assert not (plugin / "REGISTERED").exists()


def test_cli_execute_imports_register(tmp_path):
    plugin = _malicious(tmp_path)
    import hpd_cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = hpd_cli.main(["check", str(plugin), "--execute"])
    assert code == 0
    out = json.loads(buf.getvalue())
    assert (plugin / "EXECUTED").read_text(encoding="utf-8") == "module-level"
    assert (plugin / "REGISTERED").read_text(encoding="utf-8") == "register"
    assert out["schemas_executed"]["ok"]
    assert out["schemas_executed"]["tools"] == ["boom"]


def test_static_incomplete_schema_is_warning_not_exec(tmp_path):
    plugin = tmp_path / "dyn"
    plugin.mkdir()
    (plugin / "plugin.yaml").write_text(
        'name: dyn\nversion: "0.1.0"\nprovides_tools: [dyn]\n', encoding="utf-8"
    )
    (plugin / "__init__.py").write_text(
        "def _schema():\n"
        "    return {'name': 'dyn', 'description': 'n', 'parameters': {'type': 'object', 'properties': {}}}\n"
        "def register(ctx):\n"
        "    ctx.register_tool(name='dyn', toolset='dyn', schema=_schema(), handler=lambda a: None)\n",
        encoding="utf-8",
    )
    out = hpd_core.check(str(plugin))
    assert out["schemas"]["source"] == "static"
    assert out["schemas"]["resolved"] == 0
    assert any("could not statically" in w for w in out["schemas"]["warnings"])
    # No false provides_tools drift error when extraction is incomplete.
    assert not any("provides_tools" in e for e in out["manifest"].get("errors") or [])
    executed = hpd_core.check(str(plugin), execute=True)
    assert executed["schemas_executed"]["tools"] == ["dyn"]
