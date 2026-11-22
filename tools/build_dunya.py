"""Piyasa Hava Durumu — "Dünya" section (S10b). Private engine; output is derived only.

Fetches daily closes for a fixed, dated universe (tools/dunya_config.json) in GitHub
Actions and keeps them on data-feed (private side):
  data/research/world_1d/<NAME>.csv     date,close
Publishes DERIVED, rounded values only:
  data/site/dunya.json  per region: index/ETF level (rounded), % change 1g/7g/30g/YTD,
                        above/below the 20/50/200-day average (0/1), % distance to the
                        200-day average; the region's largest companies (alphabetical,
                        % changes and 0/1 flags only, no prices); commodities (rounded
                        level + unit); a reference table for metals without free daily
                        data (no prices, never invented); "Günün başlıkları" = headline +
                        source + time + link only, from official feeds listed in the config.
Order is fixed by region / asset class and alphabetical inside a list — never ranked.

Sources: Yahoo Finance chart API (personal-use terms; to be replaced by a licensed source
before any monetization). Each symbol is independent: a failure is logged and the rest
continue; a symbol that has never loaded is shown as "veri yok".
"""
import datetime as dt, html, json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_tl  # noqa: E402  (Yahoo daily fetch with retries, csv helpers, stats)

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.environ.get("DUNYA_CONFIG", os.path.join(HERE, "dunya_config.json"))
RAW_DIR = os.environ.get("WORLD_RAW_DIR", "data/research/world_1d")
SITE_OUT = os.environ.get("SITE_OUT", "data/site")
OFFLINE = os.environ.get("DUNYA_OFFLINE") == "1"     # tests / local: use stored closes only
STALE_DAYS = 7
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri"
UA = {"User-Agent": "Mozilla/5.0 (piyasa-hava-durumu; github actions)",
      "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5"}
MAX_FEED_BYTES = 2_000_000
log = {}


# ---------------------------------------------------------------- private side: closes
def safe_name(sym):
    return re.sub(r"[^A-Za-z0-9]+", "_", sym).strip("_")


def load_series(item):
    """Stored closes merged with a fresh Yahoo pull (sym, then alts). Never raises."""
    path = os.path.join(RAW_DIR, safe_name(item["sym"]) + ".csv")
    old = fetch_tl.read_csv(path)
    if OFFLINE:
        log[item["sym"]] = "offline %d" % len(old)
        return old
    errs = []
    for sym in [item["sym"]] + list(item.get("alts", [])):
        try:
            new = fetch_tl.yahoo(sym, rng="3mo" if len(old) > 300 else "2y")
            if not new:
                raise RuntimeError("empty")
            old.update(new)
            fetch_tl.write_csv(path, old)
            log[item["sym"]] = "OK %s +%d -> %d" % (sym, len(new), len(old))
            return old
        except Exception as e:
            errs.append("%s %s" % (sym, str(e)[:80]))
    log[item["sym"]] = "ERR " + " | ".join(errs) + (" (stored %d)" % len(old) if old else "")
    return old


# ---------------------------------------------------------------- derived (public side)
def nd_for(v):
    a = abs(v)
    return 0 if a >= 1000 else 2 if a >= 1 else 4


def ma_flags(series):
    d = sorted(series)
    v = [series[x] for x in d]
    out = {}
    for w in (20, 50, 200):
        out["ust%d" % w] = (1 if v[-1] > sum(v[-w:]) / w else 0) if len(v) >= w else None
    return out


def completed(series, today):
    """Drop bars dated today or later: the build runs ~06:00 UTC while Asian sessions
    (Tokyo, Seoul, Shanghai, Hong Kong) are still open and futures trade around the clock,
    so a bar for today would be a partial, intraday value. Rows show the last completed session."""
    cut = today.isoformat()
    return {d: v for d, v in series.items() if d < cut}


def row_for(series, today, with_level=True):
    series = completed(series or {}, today)
    if not series or len(series) < 2:
        return {"asof": None, "chg_1g": None, "chg_7g": None, "chg_30g": None, "chg_ytd": None,
                "ust20": None, "ust50": None, "ust200": None, "fark200": None, "eski": True}
    s = fetch_tl.stats(series)
    r = {"asof": s["asof"]}
    if with_level:
        r["seviye"] = round(s["last"], nd_for(s["last"]))
    for k in ("chg_1g", "chg_7g", "chg_30g", "chg_ytd"):
        r[k] = None if s[k] is None else round(s[k], 1)
    r.update(ma_flags(series))
    r["fark200"] = None if s["vs_ma200"] is None else round(s["vs_ma200"], 1)
    r["eski"] = (today - dt.date.fromisoformat(s["asof"])).days > STALE_DAYS
    return r


def build_markets(cfg, today, get):
    markets, missing, latest = [], [], None
    for m in cfg["markets"]:
        idx = []
        for it in m["indices"]:
            series = get(it)
            if not series and it.get("optional"):
                missing.append(it["id"])
                continue
            r = {"id": it["id"], "ad": it["name"], "tur": it["kind"]}
            r.update(row_for(series, today))
            if r["asof"] is None:
                missing.append(it["id"])
            elif not r["eski"]:
                latest = max(latest or r["asof"], r["asof"])
            idx.append(r)
        comps = []
        for c in m["companies"]:
            series = get(c)
            r = {"ad": c["name"], "kod": c["sym"]}
            r.update(row_for(series, today, with_level=False))   # companies: no price levels
            if r["asof"] is None:
                missing.append(c["sym"])
            comps.append(r)
        comps.sort(key=lambda r: r["ad"].casefold())
        markets.append({"id": m["id"], "baslik": m["title"], "endeksler": idx, "sirketler": comps})
    return markets, missing, latest


def build_commodities(cfg, today, get):
    groups, missing = [], []
    for g in cfg["commodities"]:
        rows = []
        for it in g["items"]:
            r = {"id": it["id"], "ad": it["name"], "birim": it["unit"]}
            r.update(row_for(get(it), today))
            if r["asof"] is None:
                missing.append(it["id"])
            rows.append(r)
        rows.sort(key=lambda r: r["ad"].casefold())
        groups.append({"grup": g["group"], "satirlar": rows})
    return groups, missing


# ---------------------------------------------------------------- headlines (title + source + time + link only)
TAG = re.compile(r"<[^>]+>")


def clean_title(t):
    t = html.unescape(TAG.sub(" ", html.unescape(t or "")))
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= 180 else t[:177].rstrip() + "…"


def parse_time(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def parse_feed(raw):
    """RSS 2.0 / Atom -> [(title, link, datetime)]. Refuses DTDs (entity expansion)."""
    head = raw[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in raw.lower():
        raise ValueError("DTD not allowed")
    root = ET.fromstring(raw)
    out = []

    def local(tag):
        return tag.rsplit("}", 1)[-1]

    for node in root.iter():
        name = local(node.tag)
        if name not in ("item", "entry"):
            continue
        title = link = when = guid = None
        for ch in node:
            n = local(ch.tag)
            if n == "title":
                title = "".join(ch.itertext())
            elif n == "link":
                if ch.get("href"):
                    if ch.get("rel", "alternate") == "alternate":
                        link = ch.get("href")
                elif (ch.text or "").strip():
                    link = ch.text.strip()
            elif n in ("guid", "id") and (ch.text or "").strip():
                guid = ch.text.strip()
            elif n in ("pubDate", "published", "updated", "date") and when is None:
                when = parse_time(ch.text)
        link = (link or "").strip()
        if (not link or link.endswith("=")) and guid and guid.startswith("https://") and not guid.endswith("="):
            link = guid          # some feeds (EIA) ship a link with an empty id; the guid carries the full URL
        elif link.endswith("="):
            link = ""            # an incomplete link is dropped rather than published
        out.append((clean_title(title), link, when))
    return out


def fetch_feed(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read(MAX_FEED_BYTES + 1)
    if len(raw) > MAX_FEED_BYTES:
        raise ValueError("feed too large")
    return raw


def build_headlines(hcfg, now, fetch=fetch_feed):
    max_age = dt.timedelta(days=hcfg.get("max_age_days", 4))
    excl = [w.lower() for w in hcfg.get("exclude_words", [])]
    items, sources = [], []
    for f in hcfg["feeds"]:
        st = {"kaynak": f["source"], "konu": f["topic"], "url": f["url"], "sartlar": f.get("terms", "")}
        if OFFLINE and fetch is fetch_feed:
            st["durum"] = "denenmedi (çevrimdışı)"
            sources.append(st)
            continue
        try:
            rows = parse_feed(fetch(f["url"]))
            got = []
            for title, link, when in rows:
                if not title or not link.startswith("https://") or when is None:
                    continue
                if when > now + dt.timedelta(hours=2) or now - when > max_age:
                    continue
                if any(w in title.lower() for w in excl):      # off-topic items in economy feeds (lotteries)
                    continue
                got.append({"baslik": title, "kaynak": f["source"], "url": link, "dil": f.get("lang", "en"),
                            "zaman": when.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                            "konu": f["topic"]})
            got.sort(key=lambda x: x["zaman"], reverse=True)
            got = got[:hcfg.get("max_per_feed", 3)]
            items.extend(got)
            st["durum"] = "ok (%d)" % len(got)
        except Exception as e:
            st["durum"] = "hata: %s" % type(e).__name__
        log["feed " + f["id"]] = st["durum"]
        sources.append(st)
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: x["zaman"], reverse=True):
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        uniq.append(it)
    uniq = uniq[:hcfg.get("max_total", 10)]
    topics = []
    for t in hcfg["topics"]:
        ts = [dict((k, v) for k, v in it.items() if k != "konu") for it in uniq if it["konu"] == t]
        topics.append({"konu": t, "basliklar": ts})
    return {"konular": topics, "kaynaklar": sources,
            "bekleyen": [{"konu": w["topic"], "not": w["note"]} for w in hcfg.get("waiting", [])],
            "not": "Yalnız başlık, kaynak, saat ve bağlantı. Haber metni ya da görsel kopyalanmaz; "
                   "başlıklar kaynağın kendi dilindedir ve sitenin görüşü değildir."}


# ---------------------------------------------------------------- record
def build(cfg, today=None, now=None, get=None, fetch=fetch_feed):
    now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    today = today or now.date()
    get = get or load_series
    markets, miss1, latest = build_markets(cfg, today, get)
    commodities, miss2 = build_commodities(cfg, today, get)
    heads = build_headlines(cfg["headlines"], now, fetch)
    return {"schema": "phd.dunya/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
            "generated_at": now.isoformat().replace("+00:00", "Z"), "attribution": ATTRIBUTION,
            "license": "Yalnızca görüntüleme (atıfla). Girdiler Yahoo Finance kişisel kullanım şartlı; endeks "
                       "seviyeleri endeks sağlayıcılarının lisansına tabidir. CC BY 4.0 kapsamında değil. Ayrıntı: veri.html",
            "universe_set_date": cfg.get("set_date"), "universe_review": cfg.get("review"),
            "data_date": latest, "status": "ok" if latest else "veri yok", "missing": miss1 + miss2,
            "fields": {"seviye": "son kapanış, yuvarlanmış (yalnız endeks/fon/emtia; şirketlerde yok)",
                       "chg_1g/chg_7g/chg_30g/chg_ytd": "% değişim: son işlem günü, 7 ve 30 takvim günü, yıl başı (1 ondalık)",
                       "ust20/ust50/ust200": "1 = son kapanış o günlük basit ortalamanın üstünde, 0 = altında, null = yeterli geçmiş yok",
                       "fark200": "200 günlük ortalamaya % uzaklık", "asof": "son kapanış tarihi (yerel borsa günü)",
                       "eski": "son kapanış 7 takvim gününden eski ya da veri yok"},
            "note": "Bölgeye ve varlık sınıfına göre sabit sıra, listeler alfabetik; bir performans sıralaması ya da öneri değildir. "
                    "Şirket listeleri belirlendiği tarihteki yaklaşık piyasa değeri büyüklüğüne göre seçildi ve üç ayda bir gözden geçirilir. "
                    "Borsalar farklı saat dilimlerinde kapanır; tarih sütunu her satırın kendi kapanış gününü gösterir.",
            "disclaimer": "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır.",
            "markets": markets, "emtia": commodities,
            "referans_metaller": [{"ad": r["name"], "aciklama": r["desc"], "durum": "günlük serbest veri yok"}
                                  for r in cfg.get("reference_metals", [])],
            "basliklar": heads}


def main():
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    rec = build(cfg)
    os.makedirs(SITE_OUT, exist_ok=True)
    path = os.path.join(SITE_OUT, "dunya.json")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    for k in sorted(log):
        print(k, log[k])
    nh = sum(len(t["basliklar"]) for t in rec["basliklar"]["konular"])
    print("dunya.json:", rec["data_date"], "missing", ",".join(rec["missing"]) or "-", "headlines", nh)
    if rec["missing"]:
        print("::warning::dunya: no data for " + " ".join(rec["missing"]))


if __name__ == "__main__":
    main()
