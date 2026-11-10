"""Security lint contracts; snippets are inert fixtures, never executed."""
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hpd_core import check_security


@pytest.mark.parametrize('file,source,rule', [
    ('dashboard/pane.js', 'import React from "https://esm.sh/react";', 'remote_pane_code'),
    ('dashboard/pane.js', 'window.parent.__HERMES_SESSION_TOKEN__', 'pane_token_read'),
    ('desktop/plugin.js', 'sessionStorage.getItem("hermes.webapp.session.v1:x")', 'pane_token_read'),
    ('dashboard/pane.js', 'window.fetch = patched;', 'fetch_patch'),
    ('runtime.py', 'from tools.desktop_ui import show', 'private_host_import'),
    ('runtime.py', 'import os\nx = os.getenv("SERVICE_API_KEY")', 'credential_env'),
    ('runtime.py', 'from os import environ as e\nx=e["SERVICE_TOKEN"]', 'credential_env'),
    ('runtime.py', 'import os\nx = os.environ.get("HERMES_HOME")', 'profile_env'),
    ('runtime.py', 'p = "~/.hermes/plugin-data"', 'profile_path'),
    ('runtime.py', 'import subprocess, os\nsubprocess.run(["node"], env=os.environ.copy())', 'child_env_full'),
    ('runtime.py', 'def _handler(args):\n    return {"ok": True}', 'tool_dict_result'),
])
def test_reject_known_antipatterns(tmp_path, file, source, rule):
    p = tmp_path / file; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(source)
    out = check_security(tmp_path)
    assert not out['ok']
    assert any(rule in e for e in out['errors'])
    # Findings must not echo credential names or source values.
    assert 'SERVICE_API_KEY' not in str(out)


@pytest.mark.parametrize('source,rule', [
    ('import requests\nrequests.get(url)', 'url_fetch_review'),
    ('import subprocess\nsubprocess.run(["npm"])', 'child_env_inherited'),
    ('url = "http://service.example/api"', 'insecure_http'),
    ('def _handler(args):\n    return helper(args)', 'tool_result_review'),
    ('import fcntl', 'platform_import'),
])
def test_uncertain_flows_warn(tmp_path, source, rule):
    (tmp_path / 'runtime.py').write_text(source)
    out = check_security(tmp_path)
    assert out['ok'] and any(rule in w for w in out['warnings'])


def test_safe_patterns_and_loopback(tmp_path):
    (tmp_path / 'plugin.yaml').write_text('requires_env: [SERVICE_KEY]')
    (tmp_path / 'runtime.py').write_text('''import json
from agent.secret_scope import get_secret
from hermes_constants import get_hermes_home
url = "http://127.0.0.1:9000"
def _handler(args):
    return json.dumps({"ok": True})
''')
    out = check_security(tmp_path)
    assert out['ok'] and not out['warnings']


def test_desktop_floor(tmp_path):
    p=tmp_path/'desktop/plugin.js'; p.parent.mkdir();p.write_text("ctx.rest('/proxy/v1/test')")
    assert any('desktop_rest_floor' in e for e in check_security(tmp_path)['errors'])
    (tmp_path/'plugin.yaml').write_text('requires_hermes: ">=0.23.0"')
    assert check_security(tmp_path)['ok']


def test_fixture_examples_not_runtime(tmp_path):
    p=tmp_path/'tests/bad.py';p.parent.mkdir();p.write_text('from tools.desktop_ui import show')
    assert check_security(tmp_path)['ok']


def test_shipped_runtime_passes():
    assert check_security(Path(__file__).resolve().parents[1])['ok']


def test_guarded_platform_import(tmp_path):
    (tmp_path/'runtime.py').write_text('try:\n    import fcntl\nexcept ImportError:\n    fcntl = None')
    assert not check_security(tmp_path)['warnings']


def test_requires_env_declaration(tmp_path):
    (tmp_path/'runtime.py').write_text('from agent.secret_scope import get_secret\nkey = get_secret("SERVICE_KEY")')
    assert any('secret_declaration' in w for w in check_security(tmp_path)['warnings'])
    (tmp_path/'plugin.yaml').write_text('requires_env: [SERVICE_KEY]')
    assert not check_security(tmp_path)['warnings']


def test_authed_fetch_and_relay_warnings(tmp_path):
    dash = tmp_path / "dashboard"
    dash.mkdir()
    (dash / "pane.js").write_text('SDK.authedFetch("https://other.host/x.png")')
    out = check_security(tmp_path)
    assert not out["ok"]
    assert any("authed_fetch_absolute" in e for e in out["errors"])

    (dash / "pane.js").write_text('SDK.authedFetch(assetUrl)')
    out = check_security(tmp_path)
    assert out["ok"] and any("authed_fetch_url" in w for w in out["warnings"])

    (dash / "pane.js").write_text("SDK.authedFetch('/api/plugins/demo/item')")
    out = check_security(tmp_path)
    assert out["ok"] and not any("authed_fetch" in w for w in out["warnings"])

    (dash / "pane.js").write_text("frame.postMessage(cfg, '*')")
    out = check_security(tmp_path)
    assert out["ok"] and any("postmessage_wildcard" in w for w in out["warnings"])


def test_wildcard_bind_and_null_origin(tmp_path):
    (tmp_path / "runtime.py").write_text('host = "0.0.0.0"\nALLOWED_ORIGIN = "null"\n')
    out = check_security(tmp_path)
    assert out["ok"]
    assert any("wildcard_bind" in w for w in out["warnings"])
    assert any("cors_null_origin" in w for w in out["warnings"])
