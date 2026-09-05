#!/usr/bin/env python3
"""Build a single self-contained HTML preview (CSS + images inlined).

Lets the site be previewed/verified in a remote browser without deploying.
    python3 tools/build-preview.py /tmp/preview.html
"""
import base64, mimetypes, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/preview.html"

html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
css = open(os.path.join(ROOT, "styles.css"), encoding="utf-8").read()
html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>\n{css}\n</style>")

for pat in [r'<link rel="icon"[^>]*>\n?', r'<link rel="apple-touch-icon"[^>]*>\n?',
            r'<link rel="manifest"[^>]*>\n?', r'<link rel="canonical"[^>]*>\n?']:
    html = re.sub(pat, "", html)

def inline(m):
    local = os.path.join(ROOT, m.group(2).lstrip("/"))
    if not os.path.exists(local):
        return m.group(0)
    mime = mimetypes.guess_type(local)[0] or "image/webp"
    b64 = base64.b64encode(open(local, "rb").read()).decode()
    return f'{m.group(1)}="data:{mime};base64,{b64}"'

html, n = re.subn(r'(src)="(/images/[^"]+)"', inline, html)
html = html.replace("<body>", '''<body>
<div style="position:fixed;bottom:0;left:0;right:0;z-index:999;background:#211a36;color:#fff;
 font:600 13px/1.4 system-ui,sans-serif;padding:9px 14px;text-align:center">
  PREVIEW — 3 live games, delisted titles removed &middot; not yet deployed
</div>''')
open(out, "w", encoding="utf-8").write(html)
print(f"{out}: {n} images inlined, {os.path.getsize(out)/1024:.0f} KB")
