"""sscc — validate, repair, decode and generate GS1 SSCC-18 codes.

A pure, dependency-free Python port of Binlogic's "sscc-core" TypeScript
engine (the one behind https://binlogic.io/free-tools/sscc-label-generator).

Everything is deterministic GS1 mod-10 math and format checking. Nothing here
consults the GS1 registry: a "valid" verdict means the arithmetic and
structure are right, never that the company prefix is licensed. The evidence
receipt (schema ``binlogic.sscc.v1``) states that explicitly.

Public API (TS name -> Python name):
    clean            -> clean
    checkDigit       -> check_digit
    mathSteps        -> math_steps
    validate         -> validate
    repair           -> repair
    decode           -> decode
    generate         -> generate   (opts.serialStart -> serial_start)
    receipt          -> receipt
    code128CSymbols  -> code128c_symbols
    barcodeSVG       -> barcode_svg
    hri              -> hri
    selftest         -> selftest
    VERSION          -> ENGINE_VERSION (the ported engine's version, "1.0.0")

Result dictionaries keep the TS key names (camelCase where the TS uses it,
e.g. ``serialWidth``, ``otherAIs``, ``extensionDigit``) so JSON output is
byte-compatible with the web tool and the upcoming API.
"""

from .core import (
    C128,
    ENGINE_NAME,
    ENGINE_VERSION,
    barcode_svg,
    check_digit,
    clean,
    code128c_symbols,
    decode,
    generate,
    hri,
    math_steps,
    receipt,
    repair,
    selftest,
    strip_ai,
    validate,
)

__version__ = "0.1.0"

__all__ = [
    "C128",
    "ENGINE_NAME",
    "ENGINE_VERSION",
    "__version__",
    "barcode_svg",
    "check_digit",
    "clean",
    "code128c_symbols",
    "decode",
    "generate",
    "hri",
    "math_steps",
    "receipt",
    "repair",
    "selftest",
    "strip_ai",
    "validate",
]
