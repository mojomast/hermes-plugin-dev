"""hello-hermes: minimal native Hermes plugin. Hermes calls register(ctx) at load time."""
from __future__ import annotations

import inspect
from pathlib import Path

TOOLSET = "hello-hermes"
VERSION = "0.1.0"

SCHEMA = {
    "name": "hello_hermes",
    "description": (
        "Example tool. op=greet returns a greeting for `name`; op=status returns plugin health. "
        "Call only when the user asks to test the hello-hermes plugin."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["greet", "status"]},
            "name": {"type": "string", "description": "Who to greet (op=greet)."},
        },
        "required": ["op"],
        "additionalProperties": False,
    },
}


def _handler(args: dict | None = None, **_kwargs) -> dict:
    args = args or {}
    op = args.get("op")
    if op == "status":
        return {"ok": True, "plugin": "hello-hermes", "version": VERSION}
    if op == "greet":
        who = str(args.get("name") or "world")[:80]
        return {"ok": True, "message": f"Hello, {who}!"}
    return {"ok": False, "code": "bad_op", "error": f"unknown op {op!r}", "fix": "Use op=greet or op=status."}


def _register_tool_compat(register, **kwargs) -> None:
    """Pass only keywords the host's register_tool accepts (older/newer hosts differ)."""
    try:
        params = inspect.signature(register).parameters
    except (TypeError, ValueError):
        params = {}
    if params and not any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        kwargs = {k: v for k, v in kwargs.items() if k in params}
    register(**kwargs)


def register(ctx) -> None:
    """Keep fast: no network, no heavy imports. Lazy-import heavy deps inside handlers."""
    skills_dir = Path(__file__).resolve().parent / "skills"
    if skills_dir.is_dir() and hasattr(ctx, "register_skill"):
        for child in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            if (child / "SKILL.md").is_file():
                ctx.register_skill(child.name, child / "SKILL.md")

    _register_tool_compat(
        ctx.register_tool,
        name="hello_hermes",
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=_handler,
        description=SCHEMA["description"],
    )
