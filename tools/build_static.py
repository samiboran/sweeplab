#!/usr/bin/env python3
"""Piyasa Hava Durumu — static HTML snapshots for crawlers without JavaScript.

Runs on the ASSEMBLED showcase (deploy jobs: dist/ = piyasa/ + data/site/):

    python3 tools/build_static.py dist            # data read from dist/data/site

* index.html / arsiv.html: fills the <!--S:name-->…<!--/S--> slots with today's record
  and the archive table, so the page reads correctly before (or without) JS.
* arsiv/YYYY-MM-DD.html: one script-free page per archived day (from SHOW_FROM).
* sitemap.xml + robots.txt: rebuilt with SITE_BASE (env; default = GitHub Pages
  preview URL) — set SITE_BASE to the final domain and canonicals follow.
* Data links that point at raw.githubusercontent (preview) are rewritten to the
  site's own data/site/ path, since the final host serves data next to the pages.

Only reads derived data/site files; writes only inside the given dist directory.
"""
import csv
import html
import json
import os
import re
import sys

PREVIEW_BASE = "https://samiboran.github.io/sweeplab/piyasa/"
RAW_DATA = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/"
SHOW_FROM = "2026-10-01"
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
          "Eylül", "Ekim", "Kasım", "Aralık"]
WORD = {"YESIL": "YEŞİL", "SARI": "SARI", "KIRMIZI": "KIRMIZI"}
CODES = ["L1", "L2", "L3", "D1", "K1", "K2", "K3", "N1", "P1"]
TITLES = {"L1": "Stablecoin arzı", "L2": "Fed net likiditesi", "L3": "Reel faiz", "D1": "Dolar endeksi",
          "K1": "Kredi risk primi", "K2": "Oynaklık (VIX)", "K3": "Nasdaq Bileşik", "N1": "Altın ve dolar",
          "P1": "Petrol"}
PAGES = [("", "daily"), ("arsiv.html", "daily"), ("hafta.html", "weekly"), ("konum.html", "daily"), ("hareket.html", "daily"), ("dunya.html", "daily"), ("veri.html", "monthly"),
         ("hesapla.html", "monthly"), ("yontem.html", "monthly")]
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
e = html.escape


def tr_date(iso):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso or ""))
    return f"{int(m.group(3))} {MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m else "—"


def fill(doc, name, inner):
    pat = re.compile(r"<!--S:" + re.escape(name) + r"-->.*?<!--/S-->", re.S)
    if not pat.search(doc):
        raise ValueError(f"slot {name} missing")
    return pat.sub(lambda _: f"<!--S:{name}-->{inner}<!--/S-->", doc, count=1)


def lv(code):
    return code if code in WORD else None


def meta_line(d):
    mode = {"live": "canlı", "retro": "geriye dönük"}.get(d.get("mode"), "—")
    return (f"Veri: {tr_date(d.get('data_date'))} kapanışı · Kural sürümü {e(str(d.get('rules_version') or '—'))}"
            f" · Kayıt: {mode}")


def headline(d):
    l = lv(d.get("level"))
    return f"{tr_date(d.get('publish_date'))} — Makro hava: {WORD[l]}" if l else "Makro hava verisi yok"


def rules_html(d):
    out = []
    for r in d.get("rules") or []:
        f = r.get("flag")
        cls = "on" if f == 1 else "off" if f == 0 else "na"
        out.append(f'<li class="{cls}"><span class="mark"></span><span class="body">'
                   f'<span class="rtitle">{e(str(r.get("title", "")))}</span>'
                   f'<span class="rgroup">{e(str(r.get("group", "")))}</span>'
                   f'<span class="rtext">{e(str(r.get("sentence", "")))}</span></span></li>')
    return "".join(out)


def foot(d):
    return (f"Veri tarihi {tr_date(d.get('data_date'))} · Kural sürümü {e(str(d.get('rules_version') or '—'))}"
            f" · Üretildi {e(str(d.get('generated_at') or '—').replace('T', ' ').replace('Z', ' UTC'))}")


def read_history(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if ISO.match(r.get("date", ""))]


def days_rows(hist, link_static=True):
    out = []
    for r in reversed([h for h in hist if h["date"] >= SHOW_FROM]):
        l = lv(r.get("level"))
        dot = f'<span class="dot lv-{l.lower()}" aria-hidden="true"></span>' if l else ""
        marks = "".join(f'<span class="fm{" on" if r.get(c) == "1" else ""}" title="{c} {e(TITLES[c])}"></span>'
                        for c in CODES)
        on = ", ".join(TITLES[c] for c in CODES if r.get(c) == "1") or "işaret yok"
        href = f"arsiv/{r['date']}.html" if link_static else f"./?tarih={r['date']}"
        mode = "live" if r.get("mode") == "live" else "retro"
        out.append(f'<tr class="{mode}"><td class="d"><a href="{href}">{tr_date(r["date"])}</a></td>'
                   f'<td class="lv">{dot}{WORD.get(l, "—")}</td><td class="n">{e(r.get("raw_score") or "–")}/9</td>'
                   f'<td class="flags">{marks}<span class="sr">{e(on)}</span></td>'
                   f'<td class="v">{e(r.get("rules_version") or "—")}</td>'
                   f'<td class="m">{"canlı" if mode == "live" else "geriye dönük"}</td></tr>')
    return "".join(out)


def day_page(d, base):
    day = d["data_date"]
    l = lv(d.get("level"))
    title = f"{tr_date(day)} makro hava: {WORD.get(l, '—')} — Piyasa Hava Durumu"
    desc = (f"{tr_date(day)} günü makro hava seviyesi {WORD.get(l, '—')}; dokuz kuralın işaretleri, "
            f"kural sürümü {d.get('rules_version', '—')}. Yatırım tavsiyesi değildir.")
    answers = "".join(
        f"<section><h2 class=\"sh\">{e(str(a.get('q', '')))}</h2>"
        + "".join(f"<p>{e(str(x))}</p>" for x in (a.get("a") or [])) + "</section>"
        for a in (d.get("answers") or []))
    fix = ('<p class="notice">Bu kayıtta belgelenmiş bir düzeltme var; ayrıntı Yöntem sayfasında.</p>'
           if d.get("duzeltme") else "")
    dot = f'<span class="dot lv-{l.lower()}" aria-hidden="true"></span>' if l else ""
    url = f"{base}arsiv/{day}.html"
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'; style-src 'self'; font-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'none'; object-src 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Piyasa Hava Durumu">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <a class="brand" href="../">Piyasa Hava Durumu</a>
    <nav aria-label="Site"><a href="../">Bugün</a><a href="../arsiv.html">Arşiv</a><a href="../yontem.html">Yöntem</a></nav>
  </header>
  <main id="main">
    <p class="label kick">Arşiv kaydı</p>
    <h1>{dot}{e(headline(d))}</h1>
    <p class="meta">{meta_line(d)}</p>
    {fix}
    <hr class="accent">
    <section aria-labelledby="l-kurallar">
      <p class="label" id="l-kurallar">Kurallar</p>
      <ol class="rules">{rules_html(d)}</ol>
      <p class="mute small">Ham skor {e(str(d.get('raw_score', '–')))}/{e(str(d.get('max_score', 9)))} · karşılaştırma {tr_date(d.get('compare_date'))}. <a href="../?tarih={day}">Etkileşimli görünüm</a> · <a href="../yontem.html">Yöntem</a></p>
    </section>
    {answers}
  </main>
  <footer>
    <p>Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır.</p>
    <p>{foot(d)}</p>
    <p>© Piyasa Hava Durumu — türetilmiş veriler kaynak gösterilerek kullanılabilir (CC BY 4.0)</p>
  </footer>
</div>
</body>
</html>
"""


def sitemap(base, days, lastmod):
    urls = [f"  <url><loc>{e(base + p)}</loc><lastmod>{lastmod}</lastmod><changefreq>{c}</changefreq></url>"
            for p, c in PAGES]
    urls += [f"  <url><loc>{e(base)}arsiv/{d}.html</loc><lastmod>{d}</lastmod></url>" for d in days]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")


def build(dist, data=None, base=None):
    base = base or os.environ.get("SITE_BASE") or PREVIEW_BASE
    if not base.endswith("/"):
        base += "/"
    data = data or os.path.join(dist, "data", "site")
    today = json.load(open(os.path.join(data, "today.json"), encoding="utf-8"))
    hist = read_history(os.path.join(data, "history.csv"))

    # archive day pages (script-free)
    adir = os.path.join(dist, "arsiv")
    os.makedirs(adir, exist_ok=True)
    days = []
    for h in hist:
        if h["date"] < SHOW_FROM:
            continue
        p = os.path.join(data, "archive", f"{h['date']}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        if d.get("data_date") != h["date"]:
            continue
        with open(os.path.join(adir, f"{h['date']}.html"), "w", encoding="utf-8") as f:
            f.write(day_page(d, base))
        days.append(h["date"])

    # snapshots into the JS pages
    ip = os.path.join(dist, "index.html")
    doc = open(ip, encoding="utf-8").read()
    doc = fill(doc, "headline", e(headline(today)))
    doc = fill(doc, "meta", meta_line(today))
    doc = fill(doc, "rules", rules_html(today))
    doc = fill(doc, "foot", foot(today))
    open(ip, "w", encoding="utf-8").write(doc)

    ap = os.path.join(dist, "arsiv.html")
    doc = open(ap, encoding="utf-8").read()
    doc = fill(doc, "days", days_rows([h for h in hist if h["date"] in set(days)]))
    sp = os.path.join(data, "sicil.json")
    if os.path.exists(sp):
        s = json.load(open(sp, encoding="utf-8")).get("summary_live", {})
        doc = fill(doc, "sicil-sum", e(f"Canlı kayıt: {s.get('canli_sinyal', 0)} KIRMIZI geçişi, "
                                       f"{s.get('canli_teyit', 0)} teyit, {s.get('canli_yanlis_alarm', 0)} yanlış alarm, "
                                       f"{s.get('canli_bekliyor', 0)} bekliyor."))
    open(ap, "w", encoding="utf-8").write(doc)

    # base URL + own data path in every page
    for root, _, files in os.walk(dist):
        if os.path.join(dist, "data") in root:
            continue
        for fn in files:
            if not fn.endswith((".html", ".txt", ".xml")):
                continue
            p = os.path.join(root, fn)
            t = open(p, encoding="utf-8").read()
            t2 = t.replace(RAW_DATA, base + "data/site/").replace(PREVIEW_BASE, base)
            if t2 != t:
                open(p, "w", encoding="utf-8").write(t2)

    lastmod = str(today.get("data_date") or "")[:10]
    open(os.path.join(dist, "sitemap.xml"), "w", encoding="utf-8").write(sitemap(base, days, lastmod))
    rp = os.path.join(dist, "robots.txt")
    if os.path.exists(rp):
        t = re.sub(r"(?m)^Sitemap: .*$", f"Sitemap: {base}sitemap.xml", open(rp, encoding="utf-8").read())
        open(rp, "w", encoding="utf-8").write(t)
    return {"days": len(days), "base": base}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: build_static.py DIST [DATA_DIR]")
    print(json.dumps(build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), ensure_ascii=False))
