#!/usr/bin/env python3
"""Structural sanity checks for the static HTML pages.

Uses html.parser so that we reason about real tokens rather than regex guesses.
Checks performed:

  1. Tag balance          - every container tag closes in the right order
  2. Block inside <p>     - <p> may only contain phrasing content; a nested
                            <div>/<ul>/<ol>/<section>/<h2>… is invalid and causes
                            browsers to split the paragraph
  3. Unescaped "&"        - a bare ampersand in text is invalid HTML
  4. Duplicate attributes - e.g. two class="" on one tag
  5. Duplicate ids        - ids must be unique within a document
  6. Heading order        - flag an <h3> that appears before any <h2>, which
                            usually signals a copy-paste slip

Exits non-zero if any hard problem is found.

Usage:
    python tools/check-html.py
    python tools/check-html.py --page contact.html
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import Counter
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

# Elements that may not appear inside a <p>.
NON_PHRASING_IN_P = {
    "div", "p", "ul", "ol", "li", "section", "article", "aside", "header",
    "footer", "nav", "main", "table", "h1", "h2", "h3", "h4", "h5", "h6",
    "form", "fieldset", "blockquote", "figure", "figcaption", "dl", "hr",
    "details", "summary", "address", "pre",
}

# Entities we accept without complaint when checking bare ampersands.
ENTITY_RE = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6});")


class Audit(HTMLParser):
    def __init__(self, page: str) -> None:
        super().__init__(convert_charrefs=False)
        self.page = page
        self.stack: list[tuple[str, int]] = []
        self.problems: list[str] = []
        self.ids: list[str] = []
        self.heading_seen_h2 = False
        self.first_heading: str | None = None
        self._in_raw = 0  # inside <script>/<style>, where "&" is fine

    # -- helpers ---------------------------------------------------------
    def _err(self, line: int, msg: str) -> None:
        self.problems.append(f"{self.page}:{line}  {msg}")

    # -- parser hooks ----------------------------------------------------
    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        tag = tag.lower()

        if tag in ("script", "style"):
            self._in_raw += 1

        # duplicate attributes
        names = [a[0].lower() for a in attrs]
        for name, count in Counter(names).items():
            if count > 1:
                self._err(line, f'duplicate attribute "{name}" on <{tag}>')

        for key, value in attrs:
            if key.lower() == "id" and value:
                self.ids.append(value)

        # block element opened while a <p> is still open
        if tag in NON_PHRASING_IN_P:
            for open_tag, open_line in reversed(self.stack):
                if open_tag == "p":
                    self._err(
                        open_line,
                        f"<{tag}> opened at line {line} inside <p> opened here "
                        f"(invalid nesting)",
                    )
                    break
                if open_tag not in NON_PHRASING_IN_P and open_tag != "p":
                    break

        # heading order
        if tag in ("h1", "h2", "h3", "h4"):
            if self.first_heading is None:
                self.first_heading = tag
            if tag == "h2":
                self.heading_seen_h2 = True
            elif tag == "h3" and not self.heading_seen_h2:
                self._err(line, "<h3> appears before any <h2>")

        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        # Self-closing custom usage: treat as void-like, no stack push.
        names = [a[0].lower() for a in attrs]
        for name, count in Counter(names).items():
            if count > 1:
                self._err(
                    self.getpos()[0], f'duplicate attribute "{name}" on <{tag.lower()}>'
                )

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style"):
            self._in_raw = max(0, self._in_raw - 1)
        if tag in VOID:
            return
        if not self.stack:
            self._err(self.getpos()[0], f"</{tag}> with no matching opening tag")
            return
        open_tag, open_line = self.stack[-1]
        if open_tag == tag:
            self.stack.pop()
            return
        # Not the innermost tag: either an implicit-close case or a real error.
        if tag in [t for t, _ in self.stack]:
            while self.stack and self.stack[-1][0] != tag:
                stray, stray_line = self.stack.pop()
                self._err(
                    stray_line,
                    f"<{stray}> is never closed (hit </{tag}> at line "
                    f"{self.getpos()[0]})",
                )
            if self.stack:
                self.stack.pop()
        else:
            self._err(self.getpos()[0], f"stray </{tag}>")

    def handle_data(self, data):
        if self._in_raw:
            return
        for match in re.finditer(r"&", data):
            tail = data[match.start():]
            if not ENTITY_RE.match(tail):
                self._err(self.getpos()[0], f'unescaped "&" in text: ...{tail[:40]!r}')

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass


def check(page: pathlib.Path) -> list[str]:
    parser = Audit(page.name)
    parser.feed(page.read_text(encoding="utf-8"))
    parser.close()

    problems = list(parser.problems)

    # anything left on the stack was never closed
    for tag, line in parser.stack:
        if tag not in ("html", "body"):
            problems.append(f"{page.name}:{line}  <{tag}> is never closed")

    for value, count in Counter(parser.ids).items():
        if count > 1:
            problems.append(f'{page.name}  duplicate id="{value}" ({count}x)')

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", action="append", default=None)
    args = ap.parse_args()

    pages = (
        [ROOT / name for name in args.page]
        if args.page
        else sorted(ROOT.glob("*.html"))
    )

    all_problems: list[str] = []
    for page in pages:
        all_problems.extend(check(page))

    if all_problems:
        print(f"problems: {len(all_problems)}\n")
        for item in all_problems:
            print("  -", item)
        return 1

    print(f"checked {len(pages)} page(s): no structural problems found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
