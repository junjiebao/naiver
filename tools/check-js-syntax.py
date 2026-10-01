#!/usr/bin/env python3
"""Extract every inline <script> (classic JS, not JSON-LD) and syntax-check it.

Writes each block to a temp file and runs `node --check` on it. This catches
syntax regressions in the page-level scripts that no build step would find.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = r"C:\Users\Gamer\.workbuddy\binaries\node\versions\22.22.2-3\node.exe"

SCRIPT_RE = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)


def is_classic(attrs: str) -> bool:
    a = attrs.lower()
    if "application/ld+json" in a:
        return False
    if "src=" in a:
        return False
    if "type=" in a and "javascript" not in a and "module" not in a:
        return False
    return True


def main() -> int:
    failures = 0
    checked = 0

    targets = sorted(ROOT.glob("*.html")) + sorted(ROOT.glob("js/*.js"))

    for path in targets:
        text = path.read_text(encoding="utf-8")

        if path.suffix == ".js":
            blocks = [(0, text)]
        else:
            blocks = [
                (m.start("body"), m.group("body"))
                for m in SCRIPT_RE.finditer(text)
                if is_classic(m.group("attrs"))
            ]

        for idx, (offset, body) in enumerate(blocks):
            if not body.strip():
                continue
            checked += 1
            with tempfile.NamedTemporaryFile(
                "w", suffix=".mjs", delete=False, encoding="utf-8"
            ) as fh:
                fh.write(body)
                tmp = pathlib.Path(fh.name)

            proc = subprocess.run(
                [NODE, "--check", str(tmp)],
                capture_output=True,
                text=True,
            )
            tmp.unlink(missing_ok=True)

            if proc.returncode != 0:
                failures += 1
                line = text[:offset].count("\n") + 1
                print(f"FAIL  {path.name} block#{idx} (starts near line {line})")
                for line_out in (proc.stderr or "").strip().splitlines()[:6]:
                    print("      " + line_out)

    print(f"\nsyntax-checked {checked} script block(s); failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
