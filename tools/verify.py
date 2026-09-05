#!/usr/bin/env python3
"""
Pre-flight checks for the static site.

Catches the things that silently break on a hand-maintained static site:
a referenced asset that doesn't exist, malformed JSON-LD, an unclosed tag,
a stale link. Run before pushing.

    python3 tools/verify.py
"""

import glob
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []
warnings = []
checks = 0


def ok(msg):
    global checks
    checks += 1
    print(f"  \033[32m✓\033[0m {msg}")


def bad(msg):
    errors.append(msg)
    print(f"  \033[31m✗\033[0m {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  \033[33m!\033[0m {msg}")


class TagBalance(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr", "path",
            "use", "symbol"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.problems = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack:
            self.problems.append(f"stray </{tag}> at line {self.getpos()[0]}")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            # tolerate optional-close tags
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    unclosed = [t for t, _ in self.stack[i + 1:]]
                    self.problems.append(
                        f"</{tag}> at line {self.getpos()[0]} closes over "
                        f"unclosed {unclosed}")
                    del self.stack[i:]
                    return
            self.problems.append(f"stray </{tag}> at line {self.getpos()[0]}")


def check_assets(html_file):
    """Every local href/src must resolve to a real file."""
    html = open(html_file, encoding="utf-8").read()
    name = os.path.basename(html_file)
    refs = set(re.findall(r'(?:src|href)="(/[^"#?]+|[A-Za-z0-9_][^":#?]*\.[a-z]{2,5})"', html))

    missing = []
    for ref in sorted(refs):
        if ref.startswith(("http", "mailto:", "//")):
            continue
        target = os.path.join(ROOT, ref.lstrip("/"))
        if not os.path.exists(target):
            missing.append(ref)

    if missing:
        for m in missing:
            bad(f"{name}: references missing file  {m}")
    else:
        ok(f"{name}: all {len(refs)} local asset references resolve")


def check_jsonld(html_file):
    html = open(html_file, encoding="utf-8").read()
    name = os.path.basename(html_file)
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if not blocks:
        return
    for i, block in enumerate(blocks):
        try:
            data = json.loads(block)
        except json.JSONDecodeError as e:
            bad(f"{name}: JSON-LD block {i + 1} is invalid JSON — {e}")
            continue
        graph = data.get("@graph", [data])
        types = [n.get("@type") for n in graph]
        ok(f"{name}: JSON-LD parses — {', '.join(str(t) for t in types)}")

        for node in graph:
            if node.get("@type") == "ItemList":
                n = len(node.get("itemListElement", []))
                if n:
                    ok(f"{name}: JSON-LD lists {n} games")


def check_tags(html_file):
    name = os.path.basename(html_file)
    p = TagBalance()
    p.feed(open(html_file, encoding="utf-8").read())
    leftover = [f"<{t}> (line {ln})" for t, ln in p.stack]
    if p.problems or leftover:
        for pr in p.problems:
            bad(f"{name}: {pr}")
        for lo in leftover:
            bad(f"{name}: never closed {lo}")
    else:
        ok(f"{name}: tags balanced")


def check_head(html_file):
    html = open(html_file, encoding="utf-8").read()
    name = os.path.basename(html_file)
    for label, pattern in [
        ("<title>", r"<title>[^<]+</title>"),
        ("meta description", r'name="description"'),
        ("canonical", r'rel="canonical"'),
    ]:
        if re.search(pattern, html):
            ok(f"{name}: has {label}")
        else:
            warn(f"{name}: missing {label}")


def check_json_file(path):
    name = os.path.basename(path)
    try:
        json.load(open(path, encoding="utf-8"))
        ok(f"{name}: valid JSON")
    except json.JSONDecodeError as e:
        bad(f"{name}: invalid JSON — {e}")


def check_page_weight():
    """Sum what index.html actually makes the browser download."""
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    refs = set(re.findall(r'(?:src|href)="(/[^"#?]+|styles\.css)"', html))
    total = os.path.getsize(os.path.join(ROOT, "index.html"))
    for ref in refs:
        p = os.path.join(ROOT, ref.lstrip("/"))
        if os.path.exists(p):
            total += os.path.getsize(p)
    ok(f"index.html total payload (html+css+images): {total / 1024:.0f} KB")


def main():
    print("\n\033[1mAssets\033[0m")
    pages = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    for p in pages:
        check_assets(p)

    print("\n\033[1mMarkup\033[0m")
    for p in pages:
        check_tags(p)

    print("\n\033[1mHead / SEO\033[0m")
    for p in pages:
        check_head(p)

    print("\n\033[1mStructured data\033[0m")
    for p in pages:
        check_jsonld(p)

    print("\n\033[1mConfig files\033[0m")
    check_json_file(os.path.join(ROOT, "site.webmanifest"))
    for required in ["robots.txt", "sitemap.xml", "CNAME", "favicon.ico"]:
        if os.path.exists(os.path.join(ROOT, required)):
            ok(f"{required}: present")
        else:
            bad(f"{required}: MISSING")

    print("\n\033[1mWeight\033[0m")
    check_page_weight()

    print(f"\n{'-' * 58}")
    print(f"{checks} checks passed, {len(warnings)} warnings, {len(errors)} errors")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  ! {w}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("\033[32mAll good.\033[0m")


if __name__ == "__main__":
    main()
