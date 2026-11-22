"""Piyasa Hava Durumu — daily headline card for og:image (roadmap S8).

Draws a 1200x630 PNG from the published today.json (derived data only) into
SITE_OUT/og.png: white page, near-black type, one red accent (level circle + thin
rule). No server needed: the workflow renders it each morning and the page's
og:image points at data/site/og.png (raw data-feed URL on the Pages preview,
the site's own data/site/ path on the final host — tools/build_static.py rewrites it).

Needs Pillow; without it (or on any error) the static brand card piyasa/og.png is
copied instead so the og:image URL never breaks.
"""
import json
import os
import shutil
import sys

SITE_OUT = os.environ.get("SITE_OUT", "data/site")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONTS = os.path.join(ROOT, "piyasa", "fonts")
FALLBACK = os.path.join(ROOT, "piyasa", "og.png")
W, H = 1200, 630
INK, MUTE, RED, RULE = (17, 17, 17), (110, 110, 110), (215, 38, 30), (225, 225, 225)
LEVEL_WORD = {"YESIL": "YEŞİL", "SARI": "SARI", "KIRMIZI": "KIRMIZI"}
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
          "Eylül", "Ekim", "Kasım", "Aralık"]


def tr_date(iso):
    y, m, d = (int(x) for x in iso[:10].split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


def in_latin_subset(ch):
    """Fontsource 'latin' subset ranges (the rest of Turkish is in 'latin-ext')."""
    o = ord(ch)
    return (o <= 0xFF or o in (0x131, 0x152, 0x153, 0x2C6, 0x2DA, 0x2DC, 0x20AC, 0x2122, 0x2212)
            or 0x2000 <= o <= 0x206F)


def runs(s, per_char=False):
    """Split text into runs drawn with one font file (keeps kerning inside a run)."""
    out = []
    for ch in s:
        if out and not per_char and in_latin_subset(ch) == in_latin_subset(out[-1][0]):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def card_lines(today):
    """Text content of the card — pure function (tested without Pillow)."""
    date = today.get("data_date") or today.get("last_good_date") or ""
    lw = today.get("level_word") or LEVEL_WORD.get(today.get("level"), "")
    lines = {"label": "PİYASA HAVA DURUMU",
             "date": tr_date(date) if date else "Türk yatırımcı için günlük piyasa verisi",
             "level": f"Makro hava: {lw}" if lw else "Günlük makro hava",
             "level_code": today.get("level") or "",
             "note": "",
             "foot": f"Kural sürümü {today.get('rules_version', 'v1')} · Yatırım tavsiyesi değildir."}
    if today.get("status") != "güncel":
        lines["note"] = "Güncellenmedi — son iyi kayıt gösteriliyor."
    elif today.get("level_held"):
        lines["note"] = "Seviye korundu: yeni seviye iki gün üst üste gelmedi."
    return lines


def render(today, out):
    from PIL import Image, ImageDraw, ImageFont

    def fonts(weight, size):
        return (ImageFont.truetype(os.path.join(FONTS, f"inter-latin-{weight}-normal.woff2"), size),
                ImageFont.truetype(os.path.join(FONTS, f"inter-latin-ext-{weight}-normal.woff2"), size))

    def text(draw, xy, s, fset, fill, spacing=0.0):
        x, y = xy
        for run in runs(s, per_char=spacing > 0):
            f = fset[0] if in_latin_subset(run[0]) else fset[1]
            draw.text((x, y), run, font=f, fill=fill)
            x += f.getlength(run) + spacing
        return x

    L = card_lines(today)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    m = 80
    text(d, (m, 70), L["label"], fonts(600, 22), INK, spacing=3.5)
    d.line([(m, 116), (m + 120, 116)], fill=RED, width=3)
    text(d, (m, 170), L["date"], fonts(400, 44), MUTE)
    # level circle: KIRMIZI filled red, SARI red ring, YEŞİL black ring (site rule)
    cy, r = 300, 30
    box = [m, cy - r, m + 2 * r, cy + r]
    code = L["level_code"]
    if not code:   # generic brand card (piyasa/og.png)
        text(d, (m, cy - 50), L["level"], fonts(700, 84), INK)
    elif code == "KIRMIZI":
        d.ellipse(box, fill=RED)
    elif code == "SARI":
        d.ellipse(box, outline=RED, width=7)
    else:
        d.ellipse(box, outline=INK, width=7)
    if code:
        text(d, (m + 2 * r + 34, cy - 50), L["level"], fonts(700, 84), INK)
    if L["note"]:
        text(d, (m, 390), L["note"], fonts(400, 30), RED)
    d.line([(m, 520), (W - m, 520)], fill=RULE, width=1)
    text(d, (m, 545), L["foot"], fonts(400, 24), MUTE)
    tag, tf = "Yatırım tavsiyesi değildir", fonts(400, 24)
    tw = sum((tf[0] if in_latin_subset(r[0]) else tf[1]).getlength(r) for r in runs(tag))
    text(d, (W - m - tw, 545), tag, tf, MUTE)
    img.save(out, "PNG", optimize=True)


GENERIC = {"status": "güncel", "rules_version": "v1"}


def main():
    if "--generic" in sys.argv:   # regenerate the static fallback card piyasa/og.png
        render(GENERIC, FALLBACK)
        return 0
    os.makedirs(SITE_OUT, exist_ok=True)
    out = os.path.join(SITE_OUT, "og.png")
    try:
        today = json.load(open(os.path.join(SITE_OUT, "today.json"), encoding="utf-8"))
        render(today, out)
        print("og card:", out)
        return 0
    except Exception as e:
        print("og card failed:", type(e).__name__, "- using static brand card")
        if os.path.exists(FALLBACK):
            shutil.copyfile(FALLBACK, out)
        return 1


if __name__ == "__main__":
    sys.exit(main())
