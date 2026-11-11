"""User-run CLI for hermes-plugin-dev: ``hermes hpd check <dir>``.

The default path is the same static lint as the model-facing ``hpd_check`` tool
(no import, no exec). ``--execute`` is the only way to import the target
plugin's ``register()``; it runs in this process, unsandboxed, like
``hermes plugins doctor``. Only use it on code you trust.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _core():
    if "hermes_plugin_dev_core" in sys.modules:
        return sys.modules["hermes_plugin_dev_core"]
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import hpd_core

    return hpd_core


def setup(subparser: argparse.ArgumentParser) -> None:
    """Build the argparse tree for ``hermes hpd``."""
    subparser.set_defaults(func=handler)
    subs = subparser.add_subparsers(dest="hpd_command")
    subs.required = True
    check_p = subs.add_parser(
        "check",
        help="Lint a Hermes plugin directory (static by default; never imports the plugin)",
    )
    check_p.add_argument("path", help="Plugin directory")
    check_p.add_argument(
        "--catalog",
        dest="catalog_entry",
        default="",
        help="Optional catalog YAML path",
    )
    check_p.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Also import the plugin's register() with a fake host. "
            "Runs plugin code in this process (not sandboxed); only use on code you trust. "
            "Same class of execution as `hermes plugins doctor`."
        ),
    )


def handler(args) -> int:
    if getattr(args, "hpd_command", None) != "check":
        print("Usage: hermes hpd check <dir> [--catalog PATH] [--execute]", file=sys.stderr)
        return 1
    result = _core().check(
        str(getattr(args, "path", "") or ""),
        str(getattr(args, "catalog_entry", "") or ""),
        execute=bool(getattr(args, "execute", False)),
    )
    json.dump(result, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hpd",
        description=(
            "Lint a Hermes plugin. Default is a static AST pass that never imports "
            "the target. Add --execute only when you trust the plugin code."
        ),
    )
    setup(parser)
    args = parser.parse_args(argv)
    fn = getattr(args, "func", handler)
    return int(fn(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
