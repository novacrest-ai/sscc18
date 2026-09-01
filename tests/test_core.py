"""The TS engine's 23 selftest vectors, ported verbatim from
apps/binlogic_website/src/pages/free-tools/sscc-label-generator.astro
(sscc-core 1.0.0, function `selftest`), one pytest test per `ok(...)` case,
named after the TS case labels. Plus the ported `selftest()` itself.
"""

import json

import pytest

import sscc
from sscc.cli import main as cli_main


# ---- vectors 1-7: check digit + validate ----

def test_01_cd_demo():
    assert sscc.check_digit("10614141234567890") == 8


def test_02_valid_18():
    assert sscc.validate("106141412345678908")["valid"] is True


def test_03_valid_with_00_and_spaces():
    assert sscc.validate("(00) 1 0614141 234567890 8")["valid"] is True


def test_04_valid_bare_00_20_digit():
    assert sscc.validate("00106141412345678908")["valid"] is True


def test_05_bad_check():
    assert sscc.validate("106141412345678907")["valid"] is False


def test_06_short():
    assert len(sscc.validate("1061414123456789")["errors"]) > 0


def test_07_non_digit():
    assert len(sscc.validate("10614141234567890X")["errors"]) > 0


# ---- vectors 8-11: generate ----

def test_08_generate_matches_demo():
    g = sscc.generate(prefix="0614141", ext="1", serial_start=234567890, count=1)
    assert g["list"][0] == "106141412345678908"


def test_09_serial_width_7_digit_prefix():
    g = sscc.generate(prefix="0614141", ext="1", serial_start=234567890, count=1)
    assert g["serialWidth"] == 9


def test_10_batch_3():
    g2 = sscc.generate(prefix="0614141", ext="0", serial_start=1, count=3)
    assert len(g2["list"]) == 3 and len(g2["list"][0][:17]) == 17


def test_11_batch_all_valid():
    g2 = sscc.generate(prefix="0614141", ext="0", serial_start=1, count=3)
    assert all(sscc.validate(s)["valid"] for s in g2["list"])


# ---- vectors 12-14: repair ----

def test_12_repair_finds_original():
    rep = sscc.repair("106141412345678907")
    assert any(c["sscc"] == "106141412345678908" for c in rep["substitutions"])


def test_13_17_digit_insertions_valid():
    rep17 = sscc.repair("10614141234567890")
    assert len(rep17["insertions"]) > 0
    assert all(sscc.validate(c["sscc"])["valid"] for c in rep17["insertions"])


def test_14_transposition_finds_original():
    swapped = "016141412345678908"  # pos1-2 swap of valid demo
    rep2 = sscc.repair(swapped)
    assert (
        any(c["sscc"] == "106141412345678908" for c in rep2["transpositions"])
        or len(rep2["substitutions"]) > 0
    )


# ---- vectors 15-16: decode ----

def test_15_decode_with_c1_and_extra_ai():
    d = sscc.decode("]C1(00)106141412345678908(21)12345")
    assert d["sscc"] == "106141412345678908"
    assert d["validation"]["valid"]
    assert "21" in d["otherAIs"]


def test_16_decode_without_00_errors():
    assert sscc.decode("(10)ABC123")["error"] is not None


# ---- vectors 17-21: Code 128 / SVG ----

def test_17_code128_frame():
    syms = sscc.code128c_symbols("106141412345678908")
    assert syms[0] == 105 and syms[1] == 102 and syms[-1] == 106


def test_18_code128_symbol_count():
    assert len(sscc.code128c_symbols("106141412345678908")) == 13


def test_19_code128_checksum_self_consistent():
    syms = sscc.code128c_symbols("106141412345678908")
    chk = 0
    for q in range(1, len(syms) - 2):
        chk += syms[q] * q
    chk = (105 + chk) % 103
    assert syms[-2] == chk


def test_20_pattern_table_107_entries():
    assert len(sscc.C128) == 107


def test_21_svg_renders():
    assert sscc.barcode_svg("106141412345678908")["svg"].startswith("<svg")


# ---- vectors 22-23: receipt + HRI ----

def test_22_receipt_shape():
    rc = sscc.receipt(sscc.validate("106141412345678908"))
    assert rc["schema"] == "binlogic.sscc.v1"
    assert rc["valid"] is True
    assert len(rc["unknown"]) == 2


def test_23_hri_grouping():
    assert sscc.hri("106141412345678908", 7) == "(00) 1 0614141 234567890 8"


# ---- the ported selftest itself must report 23/0, like the web console ----

def test_selftest_23_of_23():
    st = sscc.selftest()
    assert st == {"pass": 23, "fail": 0, "failures": []}


# ---- CLI smoke (JSON out, exit codes) ----

def test_cli_validate_valid_exit_0(capsys):
    assert cli_main(["validate", "106141412345678908"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["valid"] is True and out["check"]["provided"] == 8


def test_cli_validate_invalid_exit_1_and_receipt(capsys):
    assert cli_main(["validate", "106141412345678907", "--receipt"]) == 1
    rc = json.loads(capsys.readouterr().out)
    assert rc["schema"] == "binlogic.sscc.v1"
    assert rc["valid"] is False
    assert "generatedAt" in rc
    assert any("registry not consulted" in u for u in rc["unknown"])


def test_cli_generate_and_decode_roundtrip(capsys):
    assert cli_main(["generate", "--prefix", "0614141", "--ext", "1",
                     "--serial-start", "234567890", "--count", "1"]) == 0
    g = json.loads(capsys.readouterr().out)
    assert g["list"] == ["106141412345678908"]
    assert cli_main(["decode", "(00)" + g["list"][0]]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["validation"]["valid"] is True


def test_cli_generate_bad_prefix_exit_2(capsys):
    assert cli_main(["generate", "--prefix", "123", "--ext", "0",
                     "--serial-start", "1"]) == 2
    err = json.loads(capsys.readouterr().err)
    assert err["error"] == "GS1 Company Prefix must be 4-12 digits."


# ---- pinned engine error messages (TS parity) ----

def test_error_messages_match_ts():
    with pytest.raises(ValueError, match="checkDigit expects exactly 17 digits"):
        sscc.check_digit("123")
    v = sscc.validate("1061414123456789")
    assert v["errors"] == ["An SSCC has exactly 18 digits — this has 16."]
    v2 = sscc.validate("10614141234567890X")
    assert v2["errors"] == ["Contains non-digit characters — an SSCC is digits only."]
    v3 = sscc.validate("106141412345678907")
    assert v3["errors"] == ["Check digit is 7 but the mod-10 math expects 8."]
    assert sscc.validate("(00)106141412345678908")["note"] == (
        "Leading (00) Application Identifier removed."
    )
    assert sscc.validate("00106141412345678908")["note"] == (
        "Leading 00 read as the (00) Application Identifier."
    )
    with pytest.raises(ValueError, match="Serial 10000 exceeds the 4-digit space"):
        sscc.generate(prefix="061414112345", ext="0", serial_start=9999, count=2)
