# sscc

Validate, repair, decode and generate GS1 SSCC-18 codes. **Checks math and
format, never registration.**

Pure, dependency-free Python (3.9+) port of the `sscc-core` engine behind
Binlogic's free [SSCC Label Generator](https://binlogic.io/free-tools/sscc-label-generator).
Same deterministic GS1 mod-10 arithmetic, same result shapes, same
23-case selftest — and the same honesty: a *valid* verdict means the
18 digits and the check digit are mathematically right. It never means the
company prefix is licensed to anyone; no registry is consulted, and the
evidence receipt (schema `binlogic.sscc.v1`) says exactly what was checked,
what was inferred, and what stays unknown.

## Install

```sh
pip install sscc18
```

## Library

```python
import sscc

# Validate — spaces, hyphens, a leading (00) or bare 00 are normalized.
v = sscc.validate("(00) 1 0614141 234567890 8")
v["valid"]                     # True
v["check"]                     # {'provided': 8, 'expected': 8, 'algorithm': 'GS1-mod-10'}
v["structure"]["extensionDigit"]  # '1'

# Check digit for the first 17 digits.
sscc.check_digit("10614141234567890")   # 8

# Repair a mistyped code: every single-digit fix and adjacent swap
# (or, for 17 digits, every insertion) that makes the mod-10 math pass.
r = sscc.repair("106141412345678907")
r["substitutions"][0]["sscc"]  # a candidate that passes, e.g. '106141412345678908'

# Decode raw GS1-128 scan data (]C1 AIM prefix and (AI) notation handled).
d = sscc.decode("]C1(00)106141412345678908(21)9001")
d["sscc"]        # '106141412345678908'
d["otherAIs"]    # ['21'] — listed as present, not parsed

# Generate: company prefix 4-12 digits, serial fills to 17 digits + check
# digit; batches are capped at 500.
g = sscc.generate(prefix="0614141", ext="1", serial_start=234567890, count=1)
g["list"]        # ['106141412345678908']

# Evidence receipt — machine-readable record of what was (not) checked.
rc = sscc.receipt(v)
rc["schema"]     # 'binlogic.sscc.v1'
rc["unknown"]    # includes: prefix licensing (GS1 registry not consulted),
                 # and where prefix ends / serial begins (not encoded)

# GS1-128 (Code 128 subset C, leading FNC1) — symbols and an SVG barcode.
sscc.code128c_symbols("106141412345678908")   # [105, 102, ..., checksum, 106]
sscc.barcode_svg("106141412345678908")["svg"] # '<svg ...>'
sscc.hri("106141412345678908", 7)             # '(00) 1 0614141 234567890 8'

sscc.selftest()  # {'pass': 23, 'fail': 0, 'failures': []}
```

Result dicts keep the engine's original key names (`serialWidth`,
`otherAIs`, `extensionDigit`, ...) so JSON output matches the web tool and
its upcoming API byte for byte.

## CLI

All subcommands print JSON.

```sh
sscc validate 106141412345678908            # exit 0 if valid, 1 if not
sscc validate 106141412345678907 --receipt  # binlogic.sscc.v1 evidence receipt
sscc repair 10614141234567890               # 17 digits: every valid insertion
sscc decode "]C1(00)106141412345678908(21)9001"
sscc generate --prefix 0614141 --ext 0 --serial-start 1 --count 10 --hri
sscc selftest                               # the engine's 23 ported test cases
```

## What it will not tell you

Whether a company prefix is licensed, to whom, or where the prefix ends and
the serial reference begins — none of that is encoded in an SSCC, and this
package never guesses. Production SSCCs require a GS1 Company Prefix licensed
from GS1. The demo prefix `0614141` (GS1's documentation example) is for
testing and label-layout work only.

## License

MIT © Novacrest
