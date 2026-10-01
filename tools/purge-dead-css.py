#!/usr/bin/env python3
"""Remove CSS rules whose selectors reference only classes that no longer exist.

Why this exists
---------------
Pages used to pull their header and footer in at runtime from js/header.js and
js/footer.js. Those files were removed in favour of static markup, and several
page sections were rewritten, which left a long tail of rules in css/style.css
targeting classes that no host element carries any more. Dead CSS is not just
weight: it actively misleads, because a rule like `.timeline-item` makes it look
as though a feature exists.

How "dead" is decided
---------------------
A class is dead when its name appears nowhere in any .html or .js file. The host
search is a plain substring test over the concatenated sources, so a class that
is built at runtime by string concatenation still counts as live -- that is how
`form-status--sending`, assembled as 'form-status--' + state in js/forms.js, is
protected from deletion.

A rule is then removed only when every selector in it names at least one class
and at least one of those classes is dead -- one missing host is enough to make
a selector unmatchable, because `.gone .overlay` can never apply even though
`.overlay` lives on elsewhere. Selectors with no class at all (bare element
selectors such as `body` or `h2`) are never touched, a selector list is kept as
soon as a single one of its members is still live, and anything using `:is()`,
`:where()` or `:not()` is skipped because those can still match via a live
alternative.

Safety
------
Dry run by default; pass --write to apply. Nested @media / @supports bodies are
walked properly, so their inner rules are judged individually.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS_DIR = ROOT / "css"

COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/")
CLASS_RE = re.compile(r"\.([A-Za-z_][\w-]*)")

# Classes that only ever exist as the result of runtime string concatenation, so
# the literal name never appears in the sources and the substring search below
# cannot see them. js/forms.js assembles these as 'form-status--' + state, which
# is why they need to be listed by hand rather than detected.
RUNTIME_CLASSES = {
    "form-status--sending",
    "form-status--success",
    "form-status--error",
}


@dataclass
class Block:
    """One `prelude { body }` span, with the exact offsets it occupies."""

    prelude: str
    body: str
    start: int  # offset of the first character of the prelude
    body_start: int  # offset just after the opening brace
    end: int  # offset just after the closing brace

    @property
    def head(self) -> str:
        """The prelude with comments and surrounding whitespace stripped.

        Comments live inside the prelude because it spans everything between the
        previous closing brace and this opening brace. Classifying on the raw
        text would misfile an at-rule such as `@media` as an ordinary rule
        whenever a section comment precedes it, so every decision is made on
        this cleaned form.
        """
        return COMMENT_RE.sub("", self.prelude).strip()

    @property
    def is_at_rule(self) -> bool:
        return self.head.startswith("@")


def iter_blocks(text: str) -> list[Block]:
    blocks: list[Block] = []
    i = 0
    length = len(text)
    while i < length:
        brace = text.find("{", i)
        if brace == -1:
            break
        prelude = text[i:brace]
        depth = 1
        j = brace + 1
        while j < length and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        blocks.append(Block(prelude, text[brace + 1 : j - 1], i, brace + 1, j))
        i = j
    return blocks


def collect_hosts() -> str:
    """Every .html and .js file concatenated, as the pool of live class names."""
    parts: list[str] = []
    for pattern in ("*.html", "js/*.js"):
        for path in sorted(ROOT.glob(pattern)):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def find_dead_classes(plain_css: str, hosts: str) -> set[str]:
    classes: set[str] = set()
    for block in iter_blocks(plain_css):
        if not block.is_at_rule:
            classes.update(CLASS_RE.findall(block.head))
    return {name for name in classes if name not in hosts and name not in RUNTIME_CLASSES}


def selectors_of(head: str) -> list[str]:
    return [s.strip() for s in head.split(",") if s.strip()]


def is_dead_selector(selector: str, dead: set[str]) -> bool:
    """True when a selector can no longer match any element.

    A selector stops matching as soon as *one* of the classes it names has no
    host, because every compound part of the chain has to match for the whole
    selector to apply (`.gone .overlay` cannot match even though `.overlay`
    still exists elsewhere). The two negative forms would break that reasoning,
    so any selector using them is left alone.
    """
    if any(pseudo in selector for pseudo in (":is(", ":where(", ":not(")):
        return False
    classes = CLASS_RE.findall(selector)
    return bool(classes) and any(name in dead for name in classes)


def is_dead_rule(head: str, dead: set[str]) -> bool:
    selectors = selectors_of(head)
    return bool(selectors) and all(is_dead_selector(s, dead) for s in selectors)


def prune(text: str, dead: set[str], removed: list[str]) -> str:
    """Return `text` with dead rules deleted, descending into at-rules."""
    blocks = iter_blocks(text)
    if not blocks:
        return text

    out: list[str] = []
    cursor = 0
    for block in blocks:
        out.append(text[cursor : block.start])
        if block.is_at_rule:
            inner = prune(block.body, dead, removed)
            out.append(block.prelude + "{" + inner + "}")
        elif is_dead_rule(block.head, dead):
            removed.append(block.head)
        else:
            out.append(block.prelude + "{" + block.body + "}")
        cursor = block.end
    out.append(text[cursor:])
    return "".join(out)


def collapse(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="apply the changes")
    args = parser.parse_args()

    hosts = collect_hosts()
    total_rules = 0
    total_saved = 0

    for path in sorted(CSS_DIR.glob("*.css")):
        raw = path.read_text(encoding="utf-8")
        plain = COMMENT_RE.sub("", raw)
        dead = find_dead_classes(plain, hosts)
        removed: list[str] = []
        text = collapse(prune(raw, dead, removed))
        total_rules += len(removed)
        total_saved += len(raw) - len(text)

        if args.write:
            path.write_text(text, encoding="utf-8")

        print(f"{path.name}: {len(raw):,} -> {len(text):,} bytes ({len(removed)} rule(s) removed)")
        for name in removed:
            print(f"    - {name}")

    if not total_rules:
        print("\nNothing to remove: every CSS class still has a host.")

    mode = "APPLIED" if args.write else "DRY RUN (pass --write to apply)"
    print(f"\n{mode}: {total_rules} rule(s), {total_saved:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
