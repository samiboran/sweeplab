"""Piyasa Hava Durumu — "Ortalamalara göre konum" (S9). Private engine; output is derived only.

For a fixed, dated universe (tools/konum_universe.json) writes data/site/konum.json:
per asset only above/below the 20-, 50- and 200-day simple moving average (0/1) and the
rounded % distance to the 200-day average, plus the as-of date. No price levels, no OHLC,
no volume. Rows are grouped by asset class and sorted alphabetically inside a group —
never ranked by distance. Factual position table; no action words.

Inputs (data-feed, private side):
  data/research/us_1d/<SYM>.csv        date,open,high,low,close,volume   (research-data.yml)
  data/research/candles_1d/<COIN>.csv  ts,open,high,low,close,vol        (research-data.yml)
  data/derivs/okx_history_raw.json     OKX daily candles (fresher crypto closes)
  data/research/tl_1d/<NAME>.csv       date,close                        (fetch_tl.py)
"""
import csv, datetime as dt, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_charts  # noqa: E402  (reuses OKX + research crypto readers)

FEED = os.environ.get("FEED_DIR", "data")
OUT_DIR = os.environ.get("OUT_DIR", os.path.join(FEED, "derivs"))
SITE_OUT = os.environ.get("SITE_OUT", os.path.join(FEED, "site"))
US_DIR = os.environ.get("US_DIR", os.path.join(FEED, "research", "us_1d"))
CRYPTO_DIR = os.environ.get("RESEARCH_DIR", os.path.join(FEED, "research", "candles_1d"))
TL_DIR = os.environ.get("TL_RAW_DIR", os.path.join(FEED, "research", "tl_1d"))
UNIVERSE = os.environ.get("KONUM_UNIVERSE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "konum_universe.json"))
OZ = 31.1035
STALE_DAYS = 7          # an asset whose last close is older than this (calendar days) is shown as "eski"
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri, CC BY 4.0"
WINDOWS = (20, 50, 200)


def read_date_close(path):
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                c = float(r["close"])
            except (KeyError, TypeError, ValueError):
                continue
            if c > 0 and r.get("date"):
                out[r["date"][:10]] = c
    return out


def crypto_closes(coin):
    old = build_charts.RESEARCH
    build_charts.RESEARCH = CRYPTO_DIR
    try:
        closes = build_charts.research_closes(coin)
    finally:
        build_charts.RESEARCH = old
    closes.update(build_charts.okx_closes(os.path.join(OUT_DIR, "okx_history_raw.json"), coin))
    return closes


def joined(a, b, fn):
    return {d: fn(a[d], b[d]) for d in a if d in b}


def series_for(item):
    src = item.get("src")
    if src == "us":
        return read_date_close(os.path.join(US_DIR, item["id"] + ".csv"))
    if src == "crypto":
        return crypto_closes(item["id"])
    tl = lambda n: read_date_close(os.path.join(TL_DIR, n + ".csv"))
    if src == "tl":
        return tl(item["file"])
    if src == "tl_ratio":
        return joined(tl(item["file"]), tl(item["div"]), lambda x, y: x / y)
    if src == "tl_gram":
        return joined(tl(item["file"]), tl("USDTRY"), lambda x, y: x * y / OZ)
    return {}


def position(closes):
    """Last close vs 20/50/200-day simple averages. Returns None when < 20 closes."""
    d = sorted(closes)
    if len(d) < WINDOWS[0]:
        return None
    v = [closes[x] for x in d]
    last = v[-1]
    out = {"asof": d[-1]}
    for w in WINDOWS:
        if len(v) >= w:
            ma = sum(v[-w:]) / w
            out["ust%d" % w] = 1 if last > ma else 0
            if w == 200:
                out["fark200"] = round((last / ma - 1) * 100, 1)
        else:
            out["ust%d" % w] = None
            if w == 200:
                out["fark200"] = None
    return out


def count_sentence(title, rows):
    ok = [r for r in rows if r.get("ust200") is not None and not r.get("eski")]
    if not ok:
        return None
    n_up = sum(r["ust200"] for r in ok)
    return "%s: %d varlığın %d tanesi 200 günlük ortalamasının üstünde." % (title, len(ok), n_up)


def build(universe, today=None, now=None):
    today = today or dt.date.today()
    now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    groups, missing, latest = [], [], None
    for g in universe["groups"]:
        rows = []
        for it in g["items"]:
            pos = position(series_for(it))
            if pos is None:
                missing.append(it["id"])
                rows.append({"id": it["id"], "ad": it["name"], "asof": None, "ust20": None, "ust50": None,
                             "ust200": None, "fark200": None, "eski": True})
                continue
            age = (today - dt.date.fromisoformat(pos["asof"])).days
            row = {"id": it["id"], "ad": it["name"]}
            row.update(pos)
            row["eski"] = age > STALE_DAYS
            rows.append(row)
            if not row["eski"]:
                latest = max(latest or pos["asof"], pos["asof"])
        rows.sort(key=lambda r: r["ad"].casefold())     # alphabetical inside the class, never by distance
        groups.append({"id": g["id"], "baslik": g["title"], "ozet": count_sentence(g["title"], rows), "satirlar": rows})
    return {"schema": "phd.konum/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
            "generated_at": now, "attribution": ATTRIBUTION,
            "license": "Yalnızca görüntüleme (atıfla). Girdiler Yahoo Finance/OKX kişisel kullanım şartlı; CC BY 4.0 kapsamında değil. Ayrıntı: veri.html",
            "universe_set_date": universe.get("set_date"), "data_date": latest,
            "status": "ok" if latest else "veri yok", "missing": missing,
            "fields": {"ust20/ust50/ust200": "1 = son kapanış o günlük basit ortalamanın üstünde, 0 = altında, null = yeterli geçmiş yok",
                       "fark200": "son kapanışın 200 günlük ortalamaya yüzde uzaklığı (1 ondalık)",
                       "asof": "son kapanış tarihi", "eski": "son kapanış 7 takvim gününden eski ya da veri yok"},
            "note": "Olgusal konum tablosu: varlık sınıfına göre gruplu, grup içinde alfabetik. Sıralama ya da öneri değildir. "
                    "Fiyat seviyesi yayımlanmaz. Girdi kaynağı Yahoo Finance ve OKX (kişisel kullanım şartlı); "
                    "ticari kullanım öncesi lisanslı kaynakla değiştirilecek.",
            "disclaimer": "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır.",
            "groups": groups}


def main():
    universe = json.load(open(UNIVERSE, encoding="utf-8"))
    rec = build(universe)
    os.makedirs(SITE_OUT, exist_ok=True)
    path = os.path.join(SITE_OUT, "konum.json")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    print("konum.json:", rec["data_date"], "rows", sum(len(g["satirlar"]) for g in rec["groups"]),
          "missing", ",".join(rec["missing"]) or "-")


if __name__ == "__main__":
    main()
