#!/usr/bin/env python3
"""
One-off: strip the three delisted games from the site.

Kitty, Tap & Regret and Deusi Bhailo were unlisted from Play. Only Card Crush,
Crossword and Guess the Word remain live. This removes them from every surface
(hero, catalogue, footer, structured data, 404 picks, sitemap) and drops the
Culture band, which was written entirely around Deusi Bhailo and Kitty.

Copy rewrites that need human judgement are NOT done here — see the commit.

    python3 tools/remove-delisted.py
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GONE = ["kitty", "tapregret", "tap-regret", "deusibhailo", "deusi-bhailo"]
GONE_NAMES = ["Kitty", "Tap & Regret", "Deusi Bhailo"]
changes = []


def log(what, n=1):
    changes.append(f"{what} ({n})" if n != 1 else what)
    print(f"  removed: {what}" + (f"  ×{n}" if n != 1 else ""))


def rw(path, fn):
    full = os.path.join(ROOT, path)
    src = open(full, encoding="utf-8").read()
    out = fn(src)
    if out != src:
        open(full, "w", encoding="utf-8").write(out)
        return True
    return False


# ---------------------------------------------------------------- index.html
def clean_index(html):
    # 1. Hero stickers
    for slug in ["kitty", "tapregret", "deusibhailo"]:
        html, n = re.subn(
            r'\s*<a class="sticker"[^>]*id=com\.(?:gilobyte\.)?' + slug +
            r'"[^>]*>.*?</a>', "", html, flags=re.S)
        if n:
            log(f"hero sticker: {slug}", n)

    # 2. Catalogue cards (comment-anchored, articles don't nest)
    for name in GONE_NAMES:
        html, n = re.subn(
            r"\n *<!-- " + re.escape(name) + r" -->\s*"
            r'<article class="game reveal".*?</article>\n', "\n", html, flags=re.S)
        if n:
            log(f"catalogue card: {name}", n)

    # 3. Culture band — both its subjects are delisted
    html, n = re.subn(
        r"\n *<!-- CULTURE -->\s*<section id=\"culture\">.*?</section>\n",
        "\n", html, flags=re.S)
    if n:
        log("Culture section (subjects Deusi Bhailo + Kitty both delisted)")

    # 4. Nav + footer links that would now dangle
    html, n = re.subn(r'\s*<a class="lnk" href="#culture">Culture</a>', "", html)
    if n:
        log("nav link: Culture")
    html, n = re.subn(r'\s*<a href="#culture">Nepali roots</a>', "", html)
    if n:
        log("footer link: Nepali roots")

    # 5. Footer game + privacy links
    for slug in ["kitty", "tapregret", "deusibhailo"]:
        html, n = re.subn(
            r'\s*<a href="https://play\.google\.com/store/apps/details\?'
            r"id=com\.(?:gilobyte\.)?" + slug + r'"[^>]*>[^<]*</a>', "", html)
        if n:
            log(f"footer games link: {slug}", n)
    for pol in ["KITTY", "TAP_REGRET"]:
        html, n = re.subn(
            r'\s*<a href="' + pol + r'_PRIVACY_POLICY\.html">[^<]*</a>', "", html)
        if n:
            log(f"footer privacy link: {pol}", n)

    # 6. Structured data — rebuild the ItemList so positions stay 1..n
    m = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)',
                  html, re.S)
    if m:
        data = json.loads(m.group(2))
        for node in data.get("@graph", []):
            if node.get("@type") != "ItemList":
                continue
            before = len(node["itemListElement"])
            kept = [li for li in node["itemListElement"]
                    if li["item"]["name"] not in
                    ("Kitty: Card Showdown", "Tap & Regret: ZigZag Run",
                     "Deusi Bhailo")]
            for i, li in enumerate(kept, 1):
                li["position"] = i
            node["itemListElement"] = kept
            log(f"JSON-LD games: {before} → {len(kept)}, positions renumbered")
        html = (html[:m.start()] + m.group(1) + "\n" +
                json.dumps(data, indent=2) + "\n" + m.group(3) +
                html[m.end():])
    return html


# ------------------------------------------------------------------ 404.html
def clean_404(html):
    for slug in ["kitty", "tap-regret"]:
        html, n = re.subn(
            r'\s*<a href="/#games" aria-label="[^"]*">\s*'
            r'<img src="/images/apps/' + slug + r'\.webp".*?</a>',
            "", html, flags=re.S)
        if n:
            log(f"404 pick: {slug}", n)

    # Put a live game in the freed slot
    if "guess-the-word.webp" not in html:
        html = html.replace(
            '      <a href="/#games" aria-label="Crossword">\n'
            '        <img src="/images/apps/crossword.webp" alt="" width="56" '
            'height="56" loading="lazy" decoding="async">\n'
            '        <span class="lbl">Crossword</span>\n'
            '      </a>',
            '      <a href="/#games" aria-label="Crossword">\n'
            '        <img src="/images/apps/crossword.webp" alt="" width="56" '
            'height="56" loading="lazy" decoding="async">\n'
            '        <span class="lbl">Crossword</span>\n'
            '      </a>\n'
            '      <a href="/#games" aria-label="Guess the Word">\n'
            '        <img src="/images/apps/guess-the-word.webp" alt="" '
            'width="56" height="56" loading="lazy" decoding="async">\n'
            '        <span class="lbl">Guess the Word</span>\n'
            '      </a>')
        log("404 pick: added Guess the Word")
    return html


# ----------------------------------------------------------------- styles.css
def clean_css(css):
    # The whole Culture band block, comment header to next section header
    css, n = re.subn(
        r"/\* =+\n   Culture band\n   =+ \*/\n.*?(?=/\* =+\n)", "", css,
        flags=re.S)
    if n:
        log("CSS: Culture band block")
    # Its responsive overrides
    for rule in [r"\n *\.culture \.inner\{[^}]*\}",
                 r"\n *\.culture-icos\{[^}]*\}"]:
        css, n = re.subn(rule, "", css)
        if n:
            log(f"CSS: responsive override {rule[:22]}…", n)
    return css


# ----------------------------------------------------------------- sitemap
def clean_sitemap(xml):
    for pol in ["KITTY", "TAP_REGRET"]:
        xml, n = re.subn(
            r"\s*<url>\s*<loc>[^<]*" + pol + r"_PRIVACY_POLICY\.html</loc>"
            r".*?</url>", "", xml, flags=re.S)
        if n:
            log(f"sitemap entry: {pol}", n)
    return xml


def main():
    print("index.html");   rw("index.html", clean_index)
    print("404.html");     rw("404.html", clean_404)
    print("styles.css");   rw("styles.css", clean_css)
    print("sitemap.xml");  rw("sitemap.xml", clean_sitemap)

    # Unused WebP derivatives (PNG masters kept, in case anything gets relisted)
    print("assets")
    for slug in ["kitty", "tap-regret", "deusi-bhailo"]:
        p = os.path.join(ROOT, "images", "apps", f"{slug}.webp")
        if os.path.exists(p):
            os.remove(p)
            log(f"unused derivative: {slug}.webp")

    print(f"\n{len(changes)} removals applied.")


if __name__ == "__main__":
    main()
