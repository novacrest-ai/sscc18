"""sscc command-line interface.

Subcommands mirror the web tool: validate / repair / decode / generate
(plus the engine's own selftest). All output is JSON on stdout; engine
errors are JSON on stderr with exit code 2.

Exit codes: 0 = OK (validate: code is valid; decode: SSCC found and valid),
1 = check failed, 2 = usage/engine error.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, List, Optional

from . import __version__, core


def _emit(obj: Any) -> None:
    # Matches the web tool's JSON.stringify(x, null, 2): 2-space indent,
    # non-ASCII (the em-dashes in error messages) left unescaped.
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def _fail(message: str) -> int:
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    return 2


def _generated_at() -> str:
    # JS new Date().toISOString(): millisecond precision, trailing Z.
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _cmd_validate(args: argparse.Namespace) -> int:
    v = core.validate(args.code)
    if args.receipt:
        # Mirror the web page: when invalid and exactly one single-digit fix
        # exists, record it as the inferred repair.
        inferred: List[str] = []
        if not v["valid"]:
            r = core.repair(args.code)
            if len(r["substitutions"]) == 1:
                c = r["substitutions"][0]
                inferred.append(
                    "Single-digit fix at position " + str(c["position"])
                    + " (" + c["from"] + " -> " + c["to"]
                    + ") is the offered repair; it is one of "
                    + str(len(r["substitutions"]) + len(r["transpositions"]))
                    + " single-edit candidates."
                )
        rc = core.receipt(v, {"inferred": inferred})
        rc["generatedAt"] = _generated_at()
        _emit(rc)
    elif args.math:
        out = dict(v)
        out["math"] = core.math_steps(v["normalized"][:17]) if v["structure"] else None
        _emit(out)
    else:
        _emit(v)
    return 0 if v["valid"] else 1


def _cmd_repair(args: argparse.Namespace) -> int:
    _emit(core.repair(args.code))
    return 0


def _cmd_decode(args: argparse.Namespace) -> int:
    d = core.decode(args.data)
    _emit(d)
    return 0 if (d["validation"] and d["validation"]["valid"]) else 1


def _cmd_generate(args: argparse.Namespace) -> int:
    try:
        g = core.generate(
            prefix=args.prefix,
            ext=args.ext,
            serial_start=args.serial_start,
            count=args.count,
        )
    except ValueError as e:
        return _fail(str(e))
    if args.hri:
        g = dict(g)
        g["hri"] = [core.hri(s, len(g["prefix"])) for s in g["list"]]
    _emit(g)
    return 0


def _cmd_selftest(args: argparse.Namespace) -> int:
    st = core.selftest()
    _emit(st)
    return 0 if st["fail"] == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sscc",
        description=(
            "Validate, repair, decode and generate GS1 SSCC-18 codes. "
            "Checks math and format, never registration."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version="sscc " + __version__ + " (engine " + core.ENGINE_NAME + " " + core.ENGINE_VERSION + ")",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pv = sub.add_parser("validate", help="check an SSCC-18 against the GS1 mod-10 math")
    pv.add_argument("code", help="SSCC, with or without spaces/hyphens/(00)")
    pv.add_argument("--receipt", action="store_true", help="emit the binlogic.sscc.v1 evidence receipt")
    pv.add_argument("--math", action="store_true", help="include the per-digit mod-10 calculation")
    pv.set_defaults(func=_cmd_validate)

    pr = sub.add_parser("repair", help="single-edit and transposition fixes that make the math pass")
    pr.add_argument("code", help="17- or 18-digit SSCC to repair")
    pr.set_defaults(func=_cmd_repair)

    pd = sub.add_parser("decode", help="extract and check the SSCC in GS1-128 scan data")
    pd.add_argument("data", help="raw scan string, e.g. ']C1(00)106141412345678908(21)9001'")
    pd.set_defaults(func=_cmd_decode)

    pg = sub.add_parser("generate", help="mint SSCC-18 codes from a GS1 Company Prefix")
    pg.add_argument("--prefix", required=True, help="GS1 Company Prefix (4-12 digits)")
    pg.add_argument("--ext", default="0", help="extension digit 0-9 (default 0)")
    pg.add_argument("--serial-start", default="0", help="first serial reference (default 0)")
    pg.add_argument("--count", default="1", help="how many, 1-500 (default 1)")
    pg.add_argument("--hri", action="store_true", help="include human-readable groupings")
    pg.set_defaults(func=_cmd_generate)

    ps = sub.add_parser("selftest", help="run the engine's 23-case deterministic selftest")
    ps.set_defaults(func=_cmd_selftest)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
