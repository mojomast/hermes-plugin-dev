"""Print the o200k token cost of this plugin's tool schemas. pip install tiktoken pyyaml"""
import importlib.util, json, sys
from pathlib import Path
import tiktoken

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_plugin import FakeCtx, _load_plugin  # noqa: E402

ctx = FakeCtx(); _load_plugin().register(ctx)
schemas = [t["schema"] for t in ctx.tools.values()]
text = json.dumps(schemas, separators=(",", ":"), ensure_ascii=False)
enc = tiktoken.get_encoding("o200k_base")
print(f"{len(schemas)} tools, {len(enc.encode(text))} o200k tokens")
