"""Piyasa Hava Durumu — "Günün hareketlileri ve anomaliler" (S10c). Private engine.

Reads daily OHLCV for three markets and writes data/site/movers.json (derived only):
  * per market: the market index's 1-day move, top-N gainers and losers by 1-day % change
    (with relative volume), and rule-based anomalies with plain-Turkish reasons;
  * no price levels, no raw candles; symbols + rounded percentages / ratios only.
Inputs (data-feed, private side):
  bist  : data/research/bist_1d/<SYM>.csv  date,open,high,low,close,volume  (fetched here, Yahoo .IS)
  abd   : data/research/us_1d/<SYM>.csv    (research-data.yml, after the US close)
  kripto: data/research/candles_1d/<C>.csv ts,open,high,low,close,vol      (research-data.yml, OKX)
Timing: runs in daily-brief (~06:00 UTC) — BIST and US sessions of the previous day are
closed, the UTC crypto day is closed. Bars dated today (UTC) are dropped as incomplete.
"Neden?" is never written here: the page merges movers_news.json when a separate task
provides it (schema: docs/MOVERS_NEWS_SCHEMA.md); causes are never invented.
"""
import csv, datetime as dt, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.environ.get("MOVERS_CONFIG", os.path.join(HERE, "movers_config.json"))
FEED = os.environ.get("FEED_DIR", "data")
SITE_OUT = os.environ.get("SITE_OUT", os.path.join(FEED, "site"))
BIST_DIR = os.environ.get("BIST_RAW_DIR", os.path.join(FEED, "research", "bist_1d"))
US_DIR = os.environ.get("US_DIR", os.path.join(FEED, "research", "us_1d"))
CRYPTO_DIR = os.environ.get("RESEARCH_DIR", os.path.join(FEED, "research", "candles_1d"))
TL_DIR = os.environ.get("TL_RAW_DIR", os.path.join(FEED, "research", "tl_1d"))
OFFLINE = os.environ.get("MOVERS_OFFLINE") == "1"
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri"
LICENSE = "Yalnızca görüntüleme (atıfla). Girdiler Yahoo Finance/OKX kişisel kullanım şartlı; CC BY 4.0 kapsamında değil. Ayrıntı: veri.html"
UA = {"User-Agent": "Mozilla/5.0 (piyasa-hava-durumu; github actions)"}
NEDEN = "haber eşleştirmesi bekleniyor"
log = {}


# ---------------------------------------------------------------- private side: OHLCV
def read_ohlcv(path, ts_ms=False):
    """{date: (o, h, l, c, v)}; rows with a missing/zero close are skipped."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                if ts_ms:
                    d = dt.datetime.fromtimestamp(int(r["ts"]) / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
                    v = float(r.get("vol") or 0)
                else:
                    d = r["date"][:10]
                    v = float(r.get("volume") or 0)
                o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
            except (KeyError, TypeError, ValueError):
                continue
            if c > 0:
                out[d] = (o, h, l, c, v)
    return out


def write_ohlcv(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for d in sorted(data):
            o, h, l, c, v = data[d]
            w.writerow([d, "%.4f" % o, "%.4f" % h, "%.4f" % l, "%.4f" % c, "%d" % v])
    os.replace(path + ".tmp", path)


def yahoo_ohlcv(sym, rng):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (urllib.parse.quote(sym), rng)
    err = None
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            out = {}
            for i, t in enumerate(res.get("timestamp") or []):
                vals = [q[k][i] for k in ("open", "high", "low", "close")]
                if any(x is None for x in vals) or vals[3] <= 0:
                    continue
                d = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")
                out[d] = (vals[0], vals[1], vals[2], vals[3], q["volume"][i] or 0)
            if not out:
                raise RuntimeError("empty")
            return out
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, str(e)[:100])
            time.sleep(1 + a)
    raise RuntimeError(err)


def load_bist(sym):
    path = os.path.join(BIST_DIR, re.sub(r"[^A-Za-z0-9]+", "_", sym).strip("_") + ".csv")
    old = read_ohlcv(path)
    if OFFLINE:
        return old
    try:
        new = yahoo_ohlcv(sym, "3mo" if len(old) > 300 else "2y")
        old.update(new)
        write_ohlcv(path, old)
        log[sym] = "OK +%d -> %d" % (len(new), len(old))
    except Exception as e:
        log[sym] = "ERR %s (stored %d)" % (e, len(old))
    return old


def market_series(m):
    """{symbol: {date: (o,h,l,c,v)}} and the index close series {date: close}."""
    src, out = m["src"], {}
    if src == "yahoo":
        for s in m["symbols"]:
            out[s.replace(".IS", "")] = load_bist(s)
        idx = {}
        p = os.path.join(TL_DIR, m["index"]["tl_file"] + ".csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                idx = {r["date"]: float(r["close"]) for r in csv.DictReader(fh) if r.get("close")}
    elif src == "us_1d":
        ex = set(m.get("exclude", []))
        if os.path.isdir(US_DIR):
            for f in sorted(os.listdir(US_DIR)):
                s = f[:-4]
                if f.endswith(".csv") and s not in ex:
                    out[s] = read_ohlcv(os.path.join(US_DIR, f))
        idx = {d: v[3] for d, v in read_ohlcv(os.path.join(US_DIR, m["index"]["us_file"] + ".csv")).items()}
    else:
        if os.path.isdir(CRYPTO_DIR):
            for f in sorted(os.listdir(CRYPTO_DIR)):
                if f.endswith(".csv"):
                    out[f[:-4]] = read_ohlcv(os.path.join(CRYPTO_DIR, f), ts_ms=True)
        idx = {d: v[3] for d, v in out.get(m["index"]["crypto_file"], {}).items()}
    return out, idx


# ---------------------------------------------------------------- derived (public side)
def tr_num(x, nd=1):
    s = ("%." + str(nd) + "f") % abs(x)
    return s.replace(".", ",")


def tr_pct(x):
    return ("+" if x > 0 else "−" if x < 0 else "") + "%" + tr_num(x)


def atr(rows, n):
    """Wilder-free simple ATR over the n bars BEFORE the last one (no lookahead)."""
    if len(rows) < n + 2:
        return None
    trs = []
    for i in range(len(rows) - n - 1, len(rows) - 1):
        h, l, pc = rows[i][1], rows[i][2], rows[i - 1][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / n


def analyse(sym, series, idx_chg, cfg, crypto, today):
    """One symbol's last completed day. Returns None when there is not enough history."""
    a = cfg["anomaly"]
    days = sorted(d for d in series if d < today.isoformat())
    if len(days) < 22:
        return None
    rows = [series[d] for d in days]
    o, h, l, c, v = rows[-1]
    pc = rows[-2][3]
    if pc <= 0:
        return None
    chg = (c / pc - 1) * 100
    vols = [r[4] for r in rows[-21:-1]]
    avg_vol = sum(vols) / 20
    rel_vol = v / avg_vol if avg_vol > 0 else None
    turnover = sum(r[3] * r[4] for r in rows[-20:]) / 20
    gap = (o / pc - 1) * 100
    reasons, kinds = [], []
    if rel_vol is not None and rel_vol >= a["rel_vol"]:
        kinds.append("hacim")
        reasons.append("Hacim 20 günlük ortalamanın %s katı" % tr_num(rel_vol))
    gl = a["gap_crypto"] if crypto else a["gap_stock"]
    if abs(gap) >= gl:
        kinds.append("bosluk")
        reasons.append("Açılış boşluğu %s (önceki kapanışa göre)" % tr_pct(gap))
    at = atr(rows, a["atr_n"])
    if at and at > 0 and abs(c - pc) >= a["atr_mult"] * at:
        kinds.append("atr")
        reasons.append("Günlük hareket ATR(%d)'nin %s katı" % (a["atr_n"], tr_num(abs(c - pc) / at)))
    look = rows[-(a["high_low_days"] + 1):-1]
    if len(look) >= a["high_low_days"] - 5:
        if h > max(r[1] for r in look):
            kinds.append("zirve")
            reasons.append("52 haftanın en yükseği")
        elif l < min(r[2] for r in look):
            kinds.append("dip")
            reasons.append("52 haftanın en düşüğü")
    if idx_chg is not None and (chg > 0) != (idx_chg > 0) and abs(chg - idx_chg) > a["vs_index_pp"] and chg != 0:
        kinds.append("ters")
        reasons.append("Endeks %s iken %s (ters yön, %s puan fark)" % (tr_pct(idx_chg), tr_pct(chg), tr_num(abs(chg - idx_chg))))
    return {"sembol": sym, "asof": days[-1], "chg_1g": round(chg, 1),
            "rel_hacim": None if rel_vol is None else round(rel_vol, 1),
            "_turnover": turnover, "_close": c, "tur": kinds, "gerekce": reasons}


def public(r, with_reasons=False):
    out = {"sembol": r["sembol"], "chg_1g": r["chg_1g"], "rel_hacim": r["rel_hacim"]}
    if with_reasons:
        out["tur"] = r["tur"]
        out["gerekce"] = r["gerekce"]
    out["neden"] = NEDEN
    return out


def build_market(m, cfg, today, series=None, idx=None):
    if series is None:
        series, idx = market_series(m)
    crypto = m["src"] == "candles_1d"
    idays = sorted(d for d in (idx or {}) if d < today.isoformat())
    idx_chg = round((idx[idays[-1]] / idx[idays[-2]] - 1) * 100, 1) if len(idays) >= 2 else None
    idx_asof = idays[-1] if idays else None
    rows, thin = [], 0
    for sym, s in sorted(series.items()):
        r = analyse(sym, s, idx_chg, cfg, crypto, today)
        if not r:
            continue
        floor = m.get("min_turnover_20d")
        if (floor and r["_turnover"] < floor) or (m.get("min_price") and r["_close"] < m["min_price"]):
            thin += 1
            continue
        rows.append(r)
    if rows:   # only the latest common day: a symbol that stopped updating never appears as "today's mover"
        last = max(r["asof"] for r in rows)
        rows = [r for r in rows if r["asof"] == last]
    asof = rows[0]["asof"] if rows else idx_asof
    stale = asof is None or (today - dt.date.fromisoformat(asof)).days > cfg["stale_days"]
    lists = [r for r in rows if r["sembol"] not in set(m.get("exclude_from_lists", []))]
    n = cfg["top_n"]
    up = sorted([r for r in lists if r["chg_1g"] > 0], key=lambda r: (-r["chg_1g"], r["sembol"]))[:n]
    dn = sorted([r for r in lists if r["chg_1g"] < 0], key=lambda r: (r["chg_1g"], r["sembol"]))[:n]
    an = sorted([r for r in lists if r["tur"]], key=lambda r: r["sembol"])     # alphabetical, not ranked
    return {"id": m["id"], "baslik": m["title"], "asof": asof, "eski": stale,
            "endeks": {"ad": m["index"]["name"], "chg_1g": idx_chg, "asof": idx_asof},
            "evren": len(rows), "likidite_disi": thin, "not": m.get("note"),
            "yukselenler": [] if stale else [public(r) for r in up],
            "dusenler": [] if stale else [public(r) for r in dn],
            "anomaliler": [] if stale else [public(r, True) for r in an]}


def build(cfg, today=None, now=None, inputs=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    a = cfg["anomaly"]
    markets = []
    for m in cfg["markets"]:
        s, i = (inputs or {}).get(m["id"], (None, None))
        markets.append(build_market(m, cfg, today, s, i))
    return {"schema": "phd.movers/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
            "generated_at": now, "attribution": ATTRIBUTION, "license": LICENSE,
            "universe_set_date": cfg.get("set_date"),
            "kurallar": {"hacim": "Hacim 20 günlük ortalamanın en az %s katı" % tr_num(a["rel_vol"]),
                         "bosluk": "Açılış boşluğu en az ±%%%s (hisse) / ±%%%s (kripto)" % (tr_num(a["gap_stock"], 0), tr_num(a["gap_crypto"], 0)),
                         "atr": "Günlük hareket ATR(%d)'nin en az %s katı" % (a["atr_n"], tr_num(a["atr_mult"], 0)),
                         "zirve_dip": "Son 52 haftanın en yükseği ya da en düşüğü",
                         "ters": "Kendi endeksine ters yönde ve %s puandan fazla farkla" % tr_num(a["vs_index_pp"], 0)},
            "note": "Olgusal piyasa özeti: 1 günlük yüzde değişime göre en çok yükselen ve düşen isimler ile kural tabanlı "
                    "olağandışı hareketler. Fiyat seviyesi yayımlanmaz. Neden sütunu yalnız kaynaklı haber eşleşirse dolar; "
                    "neden tahmin edilmez.",
            "disclaimer": "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır.",
            "markets": markets}


def main():
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    rec = build(cfg)
    for k, v in sorted(log.items()):
        print("  %s: %s" % (k, v))
    os.makedirs(SITE_OUT, exist_ok=True)
    path = os.path.join(SITE_OUT, "movers.json")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    for m in rec["markets"]:
        print("movers %s: asof %s, %d names, %d below liquidity floor, %d anomalies%s" % (
            m["id"], m["asof"], m["evren"], m["likidite_disi"], len(m["anomaliler"]), " (ESKİ)" if m["eski"] else ""))
    if not any(m["evren"] for m in rec["markets"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
