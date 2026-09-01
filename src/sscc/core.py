"""sscc.core — pure-Python port of the Binlogic "sscc-core" TypeScript engine (v1.0.0).

Ported verbatim from the dependency-free, DOM-free ``window.SSCC`` engine that
powers https://binlogic.io/free-tools/sscc-label-generator. Behavior, result
shapes (dict key names and order), error messages, and the
``binlogic.sscc.v1`` evidence-receipt schema match the TypeScript source.

Everything here checks GS1 mod-10 *math and format only* — it never consults
the GS1 registry, so it can never tell you whether a company prefix is
licensed. The evidence receipt says so explicitly.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

ENGINE_NAME = "sscc-core"
# Version of the TypeScript engine this module ports (receipts embed it, as
# the TS engine does). The *package* version lives in sscc.__version__.
ENGINE_VERSION = "1.0.0"

# JavaScript's \s character class (as used by the TS engine), spelled out so
# Python matches JS exactly (Python's \s omits U+FEFF, JS's omits U+001C-1F).
_JS_WS = "\t\n\x0b\x0c\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"

# TS: /[\s\-‐-―]/g  (whitespace, ASCII hyphen, U+2010..U+2015 dash family)
_CLEAN_RE = re.compile("[" + _JS_WS + "\\-\u2010-\u2015]")
_TRIM_RE = re.compile("^[" + _JS_WS + "]+|[" + _JS_WS + "]+$")
_WS_RE = re.compile("[" + _JS_WS + "]")
_AI00_RE = re.compile("\\(00\\)[" + _JS_WS + "]*([0-9]{18})")
_AI_RE = re.compile(r"\(([0-9]{2,4})\)")
_JS_INT_RE = re.compile("^[" + _JS_WS + "]*([+-]?[0-9]+)")


def _to_str(raw: Any) -> str:
    """JS String(raw == null ? "" : raw)."""
    return "" if raw is None else str(raw)


def _js_parse_int(value: Any) -> Optional[int]:
    """JS parseInt(value, 10): leading whitespace/sign/digits; None plays NaN."""
    m = _JS_INT_RE.match(_to_str(value))
    return int(m.group(1)) if m else None


def _js_num(n: Union[int, float]) -> str:
    """Format a number the way JS string-concatenation does (275, not 275.0)."""
    if isinstance(n, float) and n.is_integer():
        return str(int(n))
    return str(n)


def clean(raw: Any) -> str:
    """Strip whitespace and hyphen/dash characters (TS ``clean``)."""
    return _CLEAN_RE.sub("", _to_str(raw))


def strip_ai(s: str) -> Dict[str, Optional[str]]:
    """Strip a leading AI(00) in either "(00)" or bare "00" (20-digit) form."""
    note: Optional[str] = None
    if s.startswith("(00)"):
        s = s[4:]
        note = "Leading (00) Application Identifier removed."
    elif re.fullmatch(r"00[0-9]{18}", s):
        s = s[2:]
        note = "Leading 00 read as the (00) Application Identifier."
    return {"s": s, "note": note}


def check_digit(d17: str) -> int:
    """GS1 mod-10 check digit for exactly 17 digits (TS ``checkDigit``)."""
    if not isinstance(d17, str) or not re.fullmatch(r"[0-9]{17}", d17):
        raise ValueError("checkDigit expects exactly 17 digits")
    total = 0
    for i in range(17):
        digit = ord(d17[16 - i]) - 48  # from the right
        total += digit * (3 if i % 2 == 0 else 1)  # rightmost gets 3
    return (10 - (total % 10)) % 10


def math_steps(d17: str) -> Dict[str, Any]:
    """Per-position weights/products for the mod-10 sum (TS ``mathSteps``).

    Precondition (as in TS): ``d17`` is a 17-digit string.
    """
    rows: List[Dict[str, int]] = []
    total = 0
    for i in range(17):
        digit = ord(d17[i]) - 48
        w = 3 if (16 - i) % 2 == 0 else 1
        rows.append({"pos": i + 1, "digit": digit, "weight": w, "product": digit * w})
        total += digit * w
    return {"rows": rows, "sum": total, "check": (10 - (total % 10)) % 10}


def validate(raw: Any) -> Dict[str, Any]:
    """Validate an SSCC-18; returns the TS ``validate`` result dict."""
    c = clean(raw)
    st = strip_ai(c)
    s = st["s"] or ""
    r: Dict[str, Any] = {
        "input": str(raw),
        "normalized": s,
        "note": st["note"],
        "valid": False,
        "errors": [],
        "length": len(s),
        "structure": None,
        "check": None,
    }
    if not re.fullmatch(r"[0-9]*", s):
        r["errors"].append("Contains non-digit characters \u2014 an SSCC is digits only.")
        return r
    if len(s) != 18:
        r["errors"].append("An SSCC has exactly 18 digits \u2014 this has " + str(len(s)) + ".")
        return r
    body = s[:17]
    provided = ord(s[17]) - 48
    expected = check_digit(body)
    r["structure"] = {
        "extensionDigit": s[0],
        "companyPrefixAndSerial": s[1:17],
        "checkDigit": s[17],
    }
    r["check"] = {"provided": provided, "expected": expected, "algorithm": "GS1-mod-10"}
    if provided == expected:
        r["valid"] = True
    else:
        r["errors"].append(
            "Check digit is " + str(provided)
            + " but the mod-10 math expects " + str(expected) + "."
        )
    return r


def repair(raw: Any) -> Dict[str, Any]:
    """Single-edit repair search (TS ``repair``): substitutions, adjacent
    transpositions (18-digit input) or insertions (17-digit input) that make
    the GS1 mod-10 math pass."""
    s = strip_ai(clean(raw))["s"] or ""
    out: Dict[str, Any] = {
        "substitutions": [],
        "transpositions": [],
        "insertions": [],
        "kind": None,
    }
    if not re.fullmatch(r"[0-9]+", s):
        return out
    if len(s) == 18:
        out["kind"] = "18-digit, failing"
        for i in range(18):
            for j in range(10):
                ch = chr(48 + j)
                if ch == s[i]:
                    continue
                cand = s[:i] + ch + s[i + 1:]
                if check_digit(cand[:17]) == ord(cand[17]) - 48:
                    out["substitutions"].append(
                        {"sscc": cand, "position": i + 1, "from": s[i], "to": ch}
                    )
        for i in range(17):
            if s[i] == s[i + 1]:
                continue
            cand = s[:i] + s[i + 1] + s[i] + s[i + 2:]
            if check_digit(cand[:17]) == ord(cand[17]) - 48:
                out["transpositions"].append({"sscc": cand, "positions": [i + 1, i + 2]})
    elif len(s) == 17:
        out["kind"] = "17-digit, one missing"
        for i in range(18):
            for j in range(10):
                cand = s[:i] + chr(48 + j) + s[i:]
                if check_digit(cand[:17]) == ord(cand[17]) - 48:
                    out["insertions"].append(
                        {"sscc": cand, "position": i + 1, "digit": str(j)}
                    )
    return out


def decode(raw: Any) -> Dict[str, Any]:
    """Decode GS1-128 scan data (TS ``decode``): handles a leading ``]C1`` AIM
    prefix and parenthesized AIs; extracts and validates the SSCC under (00)."""
    s = _TRIM_RE.sub("", _to_str(raw))
    if s.startswith("]C1"):
        s = s[3:]
    out: Dict[str, Any] = {"sscc": None, "otherAIs": [], "validation": None, "error": None}
    m = _AI00_RE.search(s)
    if m:
        out["sscc"] = m.group(1)
    else:
        m2 = re.match(r"00([0-9]{18})", _WS_RE.sub("", s))
        if m2:
            out["sscc"] = m2.group(1)
    for g in _AI_RE.finditer(s):
        if g.group(1) != "00":
            out["otherAIs"].append(g.group(1))
    if not out["sscc"]:
        out["error"] = "No (00) Application Identifier with 18 digits found."
        return out
    out["validation"] = validate(out["sscc"])
    return out


def generate(
    prefix: Any,
    ext: Any,
    serial_start: Any = None,
    count: Any = None,
) -> Dict[str, Any]:
    """Generate SSCC-18 codes (TS ``generate``; opts keys prefix/ext/
    serialStart/count map to these arguments). Company prefix 4-12 digits;
    serial fills to 17 digits + check digit; batch capped at 500."""
    prefix_s = clean(prefix)
    ext_s = str(ext)  # TS String(opts.ext); None fails the single-digit test, as in TS
    start = _js_parse_int(serial_start)
    c = _js_parse_int(count)
    count_n = max(1, min(500, c if c else 1))
    if not re.fullmatch(r"[0-9]{4,12}", prefix_s):
        raise ValueError("GS1 Company Prefix must be 4-12 digits.")
    if not re.fullmatch(r"[0-9]", ext_s):
        raise ValueError("Extension digit must be a single digit 0-9.")
    if not (start is not None and start >= 0):
        raise ValueError("First serial must be a non-negative number.")
    serial_width = 16 - len(prefix_s)
    max_serial = 10 ** serial_width - 1
    out_list: List[str] = []
    for k in range(count_n):
        serial = start + k
        if serial > max_serial:
            raise ValueError(
                "Serial " + str(serial) + " exceeds the " + str(serial_width)
                + "-digit space this prefix leaves."
            )
        pad = str(serial)
        while len(pad) < serial_width:
            pad = "0" + pad
        body = ext_s + prefix_s + pad
        out_list.append(body + str(check_digit(body)))
    return {"list": out_list, "serialWidth": serial_width, "prefix": prefix_s, "ext": ext_s}


def receipt(v: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evidence receipt (schema ``binlogic.sscc.v1``) for a ``validate``
    result — a machine-readable record of what was checked, what was
    inferred, and what stays unknown (registration is never checked)."""
    r: Dict[str, Any] = {
        "schema": "binlogic.sscc.v1",
        "engine": {"name": ENGINE_NAME, "version": ENGINE_VERSION, "algorithm": "GS1-mod-10"},
        "input": v["input"],
        "normalized": v["normalized"],
        "valid": v["valid"],
        "structure": v["structure"],
        "check": v["check"],
        "errors": v["errors"],
        "known": [],
        "inferred": [],
        "unknown": [
            "Whether the company prefix is licensed to the presenting party (GS1 registry not consulted).",
            "Where the company prefix ends and the serial reference begins (not encoded in the SSCC).",
        ],
    }
    if v["valid"]:
        r["known"].append("18 digits observed; GS1 mod-10 check digit verified.")
    elif v["structure"]:
        r["known"].append("18 digits observed; check digit does not satisfy GS1 mod-10.")
    else:
        r["known"].append("Input does not parse as an 18-digit SSCC.")
    if extra and extra.get("inferred"):
        r["inferred"] = extra["inferred"]
    return r


# ---------- GS1-128 (Code 128, subset C, leading FNC1) ----------
C128: List[str] = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
]


def code128c_symbols(d18: str) -> List[int]:
    """Code 128 symbol values for an SSCC-18: Start C, FNC1, nine digit
    pairs, checksum, stop (TS ``code128CSymbols``)."""
    syms = [105, 102]  # Start C, FNC1
    for i in range(0, 18, 2):
        syms.append(int(d18[i:i + 2]))
    total = 105
    pos = 1
    for k in range(1, len(syms)):
        total += syms[k] * pos
        pos += 1
    syms.append(total % 103)  # checksum
    syms.append(106)  # stop
    return syms


def barcode_svg(
    d18: str,
    opts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Render the GS1-128 barcode as an SVG string (TS ``barcodeSVG``).
    ``opts``: {"module": int (default 2), "height": int (default 90)}."""
    opts = opts or {}
    module = opts.get("module") or 2
    height = opts.get("height") or 90
    quiet = 10 * module
    syms = code128c_symbols(d18)
    x = quiet
    rects: List[str] = []
    for sym in syms:
        pat = C128[sym]
        for p in range(len(pat)):
            w = (ord(pat[p]) - 48) * module
            if p % 2 == 0:
                rects.append(
                    '<rect x="' + _js_num(x) + '" y="0" width="' + _js_num(w)
                    + '" height="' + _js_num(height) + '"/>'
                )
            x += w
    total = x + quiet
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + _js_num(total)
        + " " + _js_num(height + 26)
        + '" role="img" aria-label="GS1-128 barcode for SSCC ' + d18
        + '"><rect width="' + _js_num(total) + '" height="' + _js_num(height + 26)
        + '" fill="#fff"/><g fill="#0f1b2d">' + "".join(rects)
        + '</g><text x="' + _js_num(total / 2) + '" y="' + _js_num(height + 19)
        + '" text-anchor="middle" font-family="monospace" font-size="14" fill="#0f1b2d">(00) '
        + d18 + "</text></svg>"
    )
    return {"svg": svg, "width": total, "height": height + 26, "symbols": syms}


def hri(d18: str, prefix_len: Optional[int] = None) -> str:
    """Human-readable interpretation with extension/prefix/serial/check
    grouping when the prefix length is known (TS ``hri``)."""
    if prefix_len and 4 <= prefix_len <= 12:
        return (
            "(00) " + d18[0] + " " + d18[1:1 + prefix_len] + " "
            + d18[1 + prefix_len:17] + " " + d18[17]
        )
    return "(00) " + d18


# ---------- deterministic selftest ----------
def selftest() -> Dict[str, Any]:
    """The TS engine's 23-case deterministic selftest, ported verbatim.
    Returns {"pass": int, "fail": int, "failures": [names]}."""
    state = {"pass": 0, "fail": 0}
    msgs: List[str] = []

    def ok(cond: bool, name: str) -> None:
        if cond:
            state["pass"] += 1
        else:
            state["fail"] += 1
            msgs.append(name)

    ok(check_digit("10614141234567890") == 8, "cd demo")
    ok(validate("106141412345678908")["valid"] is True, "valid 18")
    ok(validate("(00) 1 0614141 234567890 8")["valid"] is True, "valid with (00)+spaces")
    ok(validate("00106141412345678908")["valid"] is True, "valid bare-00 20-digit")
    ok(validate("106141412345678907")["valid"] is False, "bad check")
    ok(len(validate("1061414123456789")["errors"]) > 0, "short")
    ok(len(validate("10614141234567890X")["errors"]) > 0, "non-digit")
    g = generate(prefix="0614141", ext="1", serial_start=234567890, count=1)
    ok(g["list"][0] == "106141412345678908", "generate matches demo")
    ok(g["serialWidth"] == 9, "serial width 7-digit prefix")
    g2 = generate(prefix="0614141", ext="0", serial_start=1, count=3)
    ok(len(g2["list"]) == 3 and len(g2["list"][0][:17]) == 17, "batch 3")
    ok(all(validate(s)["valid"] for s in g2["list"]), "batch all valid")
    rep = repair("106141412345678907")
    ok(any(c["sscc"] == "106141412345678908" for c in rep["substitutions"]), "repair finds original")
    rep17 = repair("10614141234567890")
    ok(
        len(rep17["insertions"]) > 0
        and all(validate(c["sscc"])["valid"] for c in rep17["insertions"]),
        "17-digit insertions valid",
    )
    swapped = "016141412345678908"  # pos1-2 swap of valid demo
    rep2 = repair(swapped)
    ok(
        any(c["sscc"] == "106141412345678908" for c in rep2["transpositions"])
        or len(rep2["substitutions"]) > 0,
        "transposition finds original",
    )
    d = decode("]C1(00)106141412345678908(21)12345")
    ok(
        d["sscc"] == "106141412345678908"
        and d["validation"]["valid"]
        and "21" in d["otherAIs"],
        "decode with ]C1 + extra AI",
    )
    ok(decode("(10)ABC123")["error"] is not None, "decode without 00 errors")
    syms = code128c_symbols("106141412345678908")
    ok(syms[0] == 105 and syms[1] == 102 and syms[-1] == 106, "code128 frame")
    ok(len(syms) == 13, "code128 symbol count")
    chk = 0
    for q in range(1, len(syms) - 2):
        chk += syms[q] * q
    chk = (105 + chk) % 103
    ok(syms[-2] == chk, "code128 checksum self-consistent")
    ok(len(C128) == 107, "pattern table 107 entries")
    ok(barcode_svg("106141412345678908")["svg"].startswith("<svg"), "svg renders")
    rc = receipt(validate("106141412345678908"))
    ok(
        rc["schema"] == "binlogic.sscc.v1" and rc["valid"] is True and len(rc["unknown"]) == 2,
        "receipt shape",
    )
    ok(hri("106141412345678908", 7) == "(00) 1 0614141 234567890 8", "hri grouping")
    return {"pass": state["pass"], "fail": state["fail"], "failures": msgs}
