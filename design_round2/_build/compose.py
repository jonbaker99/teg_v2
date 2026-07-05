#!/usr/bin/env python3
"""Assemble side-by-side comparison strips from the full-page screenshots.

For each theme: the three stylings' Results page (top portion) side by side,
one strip for light and one for dark. Written to screenshots/_compare-*.png.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "screenshots"

THEMES = {
    "theme-a": ["ledger", "gridline", "manila"],
    "theme-b": ["broadsheet", "order-of-merit", "pressbox"],
    "theme-c": ["scoreboard", "almanac", "floodlight"],
}

CROP_H = 1260   # top of the results page: nav, title, tabs, leaderboard, chart start
TILE_W = 860    # scale each 1280-wide shot down to this width
GAP = 14
LABEL_H = 34


def strip(theme: str, stylings: list[str], mode: str) -> None:
    tiles = []
    for s in stylings:
        p = SHOTS / f"{s}--results--{mode}.png"
        if not p.exists():
            print(f"skip {theme} {mode}: missing {p.name}")
            return
        im = Image.open(p)
        im = im.crop((0, 0, im.width, min(CROP_H, im.height)))
        ratio = TILE_W / im.width
        im = im.resize((TILE_W, int(im.height * ratio)), Image.LANCZOS)
        tiles.append((s, im))

    h = max(im.height for _, im in tiles)
    bg = (20, 20, 20) if mode == "dark" else (235, 233, 226)
    fg = (235, 233, 226) if mode == "dark" else (30, 30, 30)
    out = Image.new("RGB", (TILE_W * 3 + GAP * 4, h + LABEL_H + GAP * 2), bg)
    d = ImageDraw.Draw(out)
    for i, (s, im) in enumerate(tiles):
        x = GAP + i * (TILE_W + GAP)
        d.text((x + 2, GAP + 2), s.upper(), fill=fg)
        out.paste(im, (x, GAP + LABEL_H))
    dest = SHOTS / f"_compare-{theme}-{mode}.png"
    out.save(dest)
    print("wrote", dest.name, out.size)


def main() -> None:
    for theme, stylings in THEMES.items():
        for mode in ("light", "dark"):
            strip(theme, stylings, mode)


if __name__ == "__main__":
    main()
