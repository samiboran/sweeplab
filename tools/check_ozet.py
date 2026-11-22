"""Validator for data/site/ozet.json — "Günün özeti" (daily news digest).

The digest is written once a day by a separate scheduled Claude task (see docs/OZET_SCHEMA.md).
That task MUST run this check before pushing; the page also renders defensively.
Usage: python3 tools/check_ozet.py path/to/ozet.json   (exit 1 + reasons when invalid)
"""
import datetime as dt, json, re, sys

KONULAR = {"Türkiye", "Merkez bankaları", "Dünya ekonomisi", "Altın ve emtia", "Kripto", "Şirketler", "Asya", "Latin Amerika"}
MAX_ITEMS = 8
# recommendation / hype words (TR + EN); "öneri" alone is allowed only inside "öneri değildir"
BANNED = re.compile(
    r"(?<![\wçğıöşü])(al|sat|alın|satın|alınmalı|satılmalı|fırsat|fırsatı|ucuz|ucuzladı|pahalı|hedef fiyat|kaçırma|kaçırmayın|"
    r"tavsiye ediyoruz|öneriyoruz|buy|sell|opportunity|cheap|target price|don't miss|we recommend|to the moon)(?![\wçğıöşü])", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
URL = re.compile(r"^https://[^\s\"'<>]+$")


def problems(d, today=None):
    out = []
    today = today or dt.datetime.now(dt.timezone.utc).date()
    for k in ("schema", "schema_version", "source", "site_url", "generated_at", "attribution", "date", "items"):
        if k not in d:
            out.append("eksik alan: " + k)
    if out:
        return out
    if d["schema"] != "phd.ozet/1":
        out.append("schema phd.ozet/1 olmalı")
    try:
        day = dt.date.fromisoformat(d["date"])
        if day > today or (today - day).days > 3:
            out.append("date bugünden en çok 3 gün eski olabilir")
    except ValueError:
        out.append("date YYYY-MM-DD olmalı")
    items = d["items"]
    if not isinstance(items, list) or not (1 <= len(items) <= MAX_ITEMS):
        out.append("items 1–%d öğe olmalı" % MAX_ITEMS)
        return out
    for i, it in enumerate(items):
        p = "items[%d]: " % i
        for k in ("konu", "baslik", "ozet", "baslik_en", "ozet_en", "kaynaklar"):
            if not it.get(k):
                out.append(p + "eksik " + k)
        if it.get("konu") and it["konu"] not in KONULAR:
            out.append(p + "konu şunlardan biri olmalı: " + ", ".join(sorted(KONULAR)))
        if len(str(it.get("baslik", ""))) > 120 or len(str(it.get("baslik_en", ""))) > 120:
            out.append(p + "başlık en çok 120 karakter")
        for k in ("ozet", "ozet_en"):
            t = str(it.get(k, ""))
            if len(t) > 420:
                out.append(p + k + " en çok 420 karakter (2–3 cümle)")
        text = " ".join(str(it.get(k, "")) for k in ("baslik", "ozet", "baslik_en", "ozet_en"))
        m = BANNED.search(text.replace("öneri değildir", "").replace("not investment advice", ""))
        if m:
            out.append(p + "yasak kelime: " + m.group(0))
        if EMOJI.search(text):
            out.append(p + "emoji olmamalı")
        ks = it.get("kaynaklar") or []
        if not isinstance(ks, list) or not (1 <= len(ks) <= 3):
            out.append(p + "kaynaklar 1–3 öğe olmalı")
            continue
        for j, s in enumerate(ks):
            if not s.get("ad") or not URL.match(str(s.get("url", ""))):
                out.append(p + "kaynaklar[%d]: ad ve https url gerekli" % j)
            if s.get("zaman"):
                try:
                    dt.datetime.fromisoformat(str(s["zaman"]).replace("Z", "+00:00"))
                except ValueError:
                    out.append(p + "kaynaklar[%d].zaman ISO 8601 olmalı" % j)
    return out


def main():
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    p = problems(d)
    if p:
        print("ozet.json GEÇERSİZ:")
        for x in p:
            print(" -", x)
        sys.exit(1)
    print("ozet.json geçerli:", len(d["items"]), "öğe,", d["date"])


if __name__ == "__main__":
    main()
