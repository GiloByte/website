#!/usr/bin/env python3
"""
Generate web-optimised derivatives of the source art.

Source PNGs are left untouched — they're the store-quality masters. This only
adds right-sized WebP (plus a JPEG social card and favicon set) that the site
actually loads. Re-run after replacing any master image.

    python3 tools/optimize-images.py
"""

import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def p(*parts):
    return os.path.join(ROOT, *parts)


def kb(path):
    return os.path.getsize(path) / 1024


def save_webp(src, dst, size, quality=82):
    """Right-size and encode to WebP, preserving alpha."""
    im = Image.open(src)
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    im.thumbnail(size, Image.LANCZOS)
    im.save(dst, "WEBP", quality=quality, method=6)
    return im.size


def save_jpeg(src, dst, size, quality=82):
    """Flatten onto the brand cream background and encode progressive JPEG."""
    im = Image.open(src).convert("RGBA")
    im.thumbnail(size, Image.LANCZOS)
    flat = Image.new("RGB", im.size, (255, 247, 240))  # --bg #fff7f0
    flat.paste(im, mask=im.split()[-1])
    flat.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
    return flat.size


def main():
    saved_before = 0.0
    saved_after = 0.0
    rows = []

    # ---- App icons -------------------------------------------------------
    # Rendered at 150px (hero) and 72/96px (cards). 320px covers 2x DPR.
    icons = [
        "card-crush",
        "crossword",
        "kitty",
        "tap-regret",
        "guess-the-word",
        "deusi-bhailo",
    ]
    for name in icons:
        src = p("images", "apps", f"{name}.png")
        dst = p("images", "apps", f"{name}.webp")
        dims = save_webp(src, dst, (320, 320))
        rows.append((f"{name}.webp", dims, kb(src), kb(dst)))
        saved_before += kb(src)
        saved_after += kb(dst)

    # ---- Gameplay screenshot --------------------------------------------
    # Rendered at 230x498 → 460x996 covers 2x DPR.
    src = p("images", "apps", "shot-card-crush.png")
    dst = p("images", "apps", "shot-card-crush.webp")
    dims = save_webp(src, dst, (460, 996), quality=80)
    rows.append(("shot-card-crush.webp", dims, kb(src), kb(dst)))
    saved_before += kb(src)
    saved_after += kb(dst)

    # ---- Social card -----------------------------------------------------
    # og:image. JPEG, not WebP — some social scrapers still don't take WebP.
    # 1200x630 is the canonical OG size.
    src = p("images", "banner.png")
    dst = p("images", "banner.jpg")
    dims = save_jpeg(src, dst, (1200, 630), quality=84)
    rows.append(("banner.jpg", dims, kb(src), kb(dst)))
    saved_before += kb(src)
    saved_after += kb(dst)

    # ---- Favicons / PWA icons -------------------------------------------
    logo = p("images", "logo.png")
    for size, out in [
        (32, "favicon-32.png"),
        (180, "apple-touch-icon.png"),
        (192, "icon-192.png"),
        (512, "icon-512.png"),
    ]:
        im = Image.open(logo).convert("RGBA")
        im.thumbnail((size, size), Image.LANCZOS)
        dst = p("images", out)
        im.save(dst, "PNG", optimize=True)
        rows.append((out, im.size, 0, kb(dst)))

    # favicon.ico for legacy / bookmark bars
    im = Image.open(logo).convert("RGBA")
    im.save(
        p("favicon.ico"),
        "ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )
    rows.append(("favicon.ico", (48, 48), 0, kb(p("favicon.ico"))))

    # ---- Report ----------------------------------------------------------
    w = max(len(r[0]) for r in rows)
    print(f"{'file'.ljust(w)}  {'dimensions':>12}  {'before':>9}  {'after':>9}")
    print("-" * (w + 38))
    for name, dims, before, after in rows:
        d = f"{dims[0]}x{dims[1]}"
        b = f"{before:.1f} KB" if before else "—"
        print(f"{name.ljust(w)}  {d:>12}  {b:>9}  {after:8.1f} KB")

    print("-" * (w + 38))
    print(f"page-weight images: {saved_before:.0f} KB → {saved_after:.0f} KB "
          f"({100 * (1 - saved_after / saved_before):.0f}% smaller)")


if __name__ == "__main__":
    main()
