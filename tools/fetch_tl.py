"""TL layer for Piyasa Hava Durumu (S4).

Private engine. Pulls daily closes and keeps them on data-feed (private side):
  data/research/tl_1d/<name>.csv   date,close   (USDTRY, GOLD_USD, SILVER_USD, XU100)
Publishes DERIVED, rounded values only:
  data/site/tl.json   gram altın TL, gram gümüş TL, dolar/TL, BIST 100 (TL and USD terms):
                      last value, % changes 1g/7g/30g/YTD, % vs 200-day MA, a short
                      derived series for small charts, BTC/ETH reference prices.

Sources (Yahoo Finance chart API, personal-use terms — to be replaced by a licensed
or public source before any monetization):
  TRY=X (USD/TRY), GC=F (COMEX gold, USD/oz), SI=F (COMEX silver, USD/oz), XU100.IS,
  BTC-USD, ETH-USD (for the 1-year view; the calculator prefers OKX closes from the notebook),
  BZ=F, CL=F (Brent / WTI oil, top band only: last value + 1-day change)
TCMB today.xml (public): USD banknote buying/selling -> makas_ref, the calculator's spread reference.
First run (or a store that is not daily) backfills daily bars from 2000 via
period1/period2 (range=max returns MONTHLY bars); later runs fetch 1 year and merge. Each symbol is independent: a failure is logged and the rest continue.
BIST 100 index level is published only as the current rounded level (needed by the
calculator); its series is published only as BIST 100 in USD, rebased to 100.
"""
import csv, datetime as dt, json, os, sys, time, urllib.parse, urllib.request

RAW_DIR = os.environ.get("TL_RAW_DIR", "data/research/tl_1d")
SITE_OUT = os.environ.get("SITE_OUT", "data/site")
NOTEBOOK = os.environ.get("NOTEBOOK", "data/derivs/notebook_daily.json")
OZ_GRAM = 31.1035
SERIES_DAYS = 400          # calendar days of derived series kept for small charts (> 1 year)
UA = {"User-Agent": "Mozilla/5.0 (piyasa-hava-durumu; github actions)"}
SYMBOLS = {"USDTRY": "TRY=X", "GOLD_USD": "GC=F", "SILVER_USD": "SI=F", "XU100": "XU100.IS",
           "BTC_USD": "BTC-USD", "ETH_USD": "ETH-USD",
           # long history for 'Dünyada bu Pazartesi/Cuma' (fund prices, not licensed index levels)
           "SPY": "SPY", "QQQ": "QQQ",
           # top band alternates (ons altın/gümüş come from GOLD_USD/SILVER_USD)
           "BRENT_USD": "BZ=F", "WTI_USD": "CL=F"}
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri, CC BY 4.0"
DATA_NOTE = ("Hesaplama: gram altın TL = ons altın (USD) × USD/TRY ÷ 31,1035; gram gümüş aynı şekilde. "
             "Girdi kaynağı Yahoo Finance (kişisel kullanım şartlı); ticari kullanım öncesi lisanslı kaynakla değiştirilecek.")
status = {}


# ---------------------------------------------------------------- fetch / store (private side)
def yahoo(symbol, start=None, rng="1y"):
    """Daily closes. Uses period1/period2 for long history: Yahoo silently returns
    MONTHLY bars for range=max even with interval=1d."""
    if start:
        p1 = int(dt.datetime.fromisoformat(start).replace(tzinfo=dt.timezone.utc).timestamp())
        p2 = int(time.time()) + 86400
        q = f"period1={p1}&period2={p2}&interval=1d"
    else:
        q = f"range={rng}&interval=1d"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{q}"
    err = None
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                j = json.loads(r.read())
            res = j["chart"]["result"][0]
            out = {}
            for t, c in zip(res.get("timestamp") or [], res["indicators"]["quote"][0]["close"]):
                if c is not None and c > 0:
                    out[dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")] = float(c)
            if not is_daily(out):
                raise RuntimeError("not daily bars (median gap > 4 days)")
            return out
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(err)


def is_daily(series):
    """True when the last 2 years look like daily bars (median gap <= 4 days)."""
    d = sorted(series)
    if len(d) < 20:
        return len(d) > 0
    cut = (dt.date.fromisoformat(d[-1]) - dt.timedelta(days=730)).isoformat()
    d = [x for x in d if x >= cut]
    gaps = sorted((dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days for a, b in zip(d, d[1:]))
    return bool(gaps) and gaps[len(gaps) // 2] <= 4


def read_csv(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {r["date"]: float(r["close"]) for r in csv.DictReader(fh) if r.get("close")}


def write_csv(path, series):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "close"])
        for d in sorted(series):
            w.writerow([d, f"{series[d]:.6f}"])
    os.replace(tmp, path)


BACKFILL_START = "2000-01-01"


def update_raw():
    data = {}
    for name, sym in SYMBOLS.items():
        path = os.path.join(RAW_DIR, name + ".csv")
        old = read_csv(path)
        try:
            if len(old) > 1000 and is_daily(old):
                new = yahoo(sym, rng="1y")
                old.update(new)
            else:   # first run, or a store polluted by monthly bars: rebuild from daily history
                new = yahoo(sym, start=BACKFILL_START)
                old = dict(new)
            write_csv(path, old)
            status[name] = f"OK {sym} +{len(new)} -> {len(old)} ({min(old)}..{max(old)})"
        except Exception as e:
            status[name] = f"ERR {sym} {e}"
            if not is_daily(old):
                old = {}     # never derive from non-daily bars
        data[name] = old
    return data


# ---------------------------------------------------------------- derived (public side)
def combine(a, b, fn):
    """Series on a's dates, b forward-filled (b may miss a holiday)."""
    out, last = {}, None
    bd = sorted(b)
    j = 0
    for d in sorted(a):
        while j < len(bd) and bd[j] <= d:
            last = b[bd[j]]
            j += 1
        if last is not None:
            out[d] = fn(a[d], last)
    return out


def value_on_or_before(series, dates, day):
    lo = None
    for d in dates:
        if d <= day:
            lo = d
        else:
            break
    return None if lo is None else series[lo]


def stats(series):
    """Last value, % changes (1g by row, 7g/30g by calendar, YTD vs last close of prior year), % vs MA200."""
    if not series:
        return None
    dates = sorted(series)
    last_d, last = dates[-1], series[dates[-1]]
    ld = dt.date.fromisoformat(last_d)
    pc = lambda base: None if base in (None, 0) else round((last / base - 1) * 100, 2)
    prev = series[dates[-2]] if len(dates) > 1 else None
    w7 = value_on_or_before(series, dates, (ld - dt.timedelta(days=7)).isoformat())
    w30 = value_on_or_before(series, dates, (ld - dt.timedelta(days=30)).isoformat())
    ytd = value_on_or_before(series, dates, f"{ld.year - 1}-12-31")
    ma200 = sum(series[d] for d in dates[-200:]) / 200 if len(dates) >= 200 else None
    d1y = (ld - dt.timedelta(days=365)).isoformat()
    y1d = max((d for d in dates if d <= d1y), default=None)
    y1 = series[y1d] if y1d and (dt.date.fromisoformat(d1y) - dt.date.fromisoformat(y1d)).days <= 7 else None
    return {"asof": last_d, "last": last, "chg_1g": pc(prev), "chg_7g": pc(w7), "chg_30g": pc(w30),
            "chg_ytd": pc(ytd), "chg_1y": pc(y1), "val_1y": y1, "date_1y": y1d if y1 is not None else None,
            "vs_ma200": pc(ma200), "ma200": ma200}


def chart_series(series, days=SERIES_DAYS, nd=2, rebase=False):
    """Last `days` CALENDAR days (≈ 13 months, so "1 year ago" is on the chart)."""
    dates = sorted(series)
    vals = [series[d] for d in dates]
    out = []
    cut = (dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=days)).isoformat() if dates else ""
    for i in range(len(dates)):
        if dates[i] < cut:
            continue
        ma = sum(vals[i - 199:i + 1]) / 200 if i >= 199 else None
        out.append([dates[i], vals[i], ma])
    if rebase and out:
        base = out[0][1]
        out = [[d, v / base * 100, None if m is None else m / base * 100] for d, v, m in out]
    return [[d, round(v, nd), None if m is None else round(m, nd)] for d, v, m in out]


def weekday_age(asof, today):
    a, t = dt.date.fromisoformat(asof), dt.date.fromisoformat(today)
    n = 0
    while a < t:
        a += dt.timedelta(days=1)
        if a.weekday() < 5:
            n += 1
    return n


def crypto_refs(path):
    try:
        rows = sorted(json.load(open(path, encoding="utf-8"))["rows"], key=lambda r: r["date"])
        last = rows[-1]
        out = {}
        for k in ("btc", "eth"):
            t = (last.get("regime") or {}).get("trend_" + k) or {}
            if t.get("close"):
                out[k] = {"asof": last["date"], "usd": round(float(t["close"]), 2)}
        return out
    except Exception:
        return {}


def derive(data, today, crypto=None):
    usd, gold, silver, xu = (data.get(k) or {} for k in ("USDTRY", "GOLD_USD", "SILVER_USD", "XU100"))
    gram_gold = combine(gold, usd, lambda g, u: g * u / OZ_GRAM) if gold and usd else {}
    gram_silver = combine(silver, usd, lambda s, u: s * u / OZ_GRAM) if silver and usd else {}
    xu_usd = combine(xu, usd, lambda x, u: x / u) if xu and usd else {}
    assets = []

    def add(aid, label, unit, series, nd, chart_nd, show_level=True, rebase=False, note=None):
        s = stats(series)
        if not s:
            assets.append({"id": aid, "label": label, "status": "veri yok"})
            return
        item = {"id": aid, "label": label, "unit": unit, "asof": s["asof"],
                "last": round(s["last"], nd) if show_level else None,
                "chg_1g": s["chg_1g"], "chg_7g": s["chg_7g"], "chg_30g": s["chg_30g"], "chg_ytd": s["chg_ytd"],
                "chg_1y": s["chg_1y"], "date_1y": s["date_1y"],
                "val_1y": round(s["val_1y"], nd) if (show_level and s["val_1y"] is not None) else None,
                "vs_ma200": s["vs_ma200"], "stale": weekday_age(s["asof"], today) > 3,
                "series": chart_series(series, nd=chart_nd, rebase=rebase)}
        if note:
            item["note"] = note
        assets.append(item)

    add("gram_altin", "Gram altın", "TL/gram", gram_gold, 2, 2)
    add("gram_gumus", "Gram gümüş", "TL/gram", gram_silver, 2, 3)
    add("dolar", "Dolar/TL", "TL", usd, 4, 4)
    add("bist100_usd", "BIST 100 (dolar bazında)", "endeks, başlangıç = 100", xu_usd, 2, 2, show_level=False,
        rebase=True, note="Endeks seviyesi yerine dolar bazında değişim gösterilir.")
    add("btc", "Bitcoin (dolar)", "$", data.get("BTC_USD") or {}, 0, 0)
    add("eth", "Ether (dolar)", "$", data.get("ETH_USD") or {}, 2, 2)
    # current values the calculator needs (no series)
    prices = {}
    sg, su, sx = stats(gram_gold), stats(usd), stats(xu)
    ss = stats(gram_silver)
    if su:
        prices["usdtry"] = round(su["last"], 4)
        prices["usdtry_asof"] = su["asof"]
    if sg:
        prices["gram_altin_tl"] = round(sg["last"], 2)
    if ss:
        prices["gram_gumus_tl"] = round(ss["last"], 3)
    if sx:
        prices["bist100_tl"] = round(sx["last"])
        prices["bist100_asof"] = sx["asof"]
    for k in ("btc", "eth"):                       # OKX (notebook) first, Yahoo as fallback
        v = (crypto or {}).get(k)
        y = stats(data.get(k.upper() + "_USD") or {})
        if v:
            prices[k + "_usd"], prices[k + "_asof"] = v["usd"], v["asof"]
        elif y:
            prices[k + "_usd"], prices[k + "_asof"] = round(y["last"], 2), y["asof"]
    # top band: alternate views shown on tap (ons gold/silver in USD, Brent/WTI oil) — last + 1g only
    band = {}
    for key, label, unit, src, nd in (("ons_altin", "Ons altın", "$", gold, 2), ("ons_gumus", "Ons gümüş", "$", silver, 2),
                                      ("brent", "Brent petrol", "$", data.get("BRENT_USD") or {}, 2),
                                      ("wti", "WTI petrol", "$", data.get("WTI_USD") or {}, 2)):
        s = stats(src)
        if s and s["chg_1g"] is not None:
            band[key] = {"label": label, "unit": unit, "asof": s["asof"], "last": round(s["last"], nd),
                         "chg_1g": s["chg_1g"], "stale": weekday_age(s["asof"], today) > 3}
    core_ok = all(a.get("asof") and not a.get("stale") for a in assets if a["id"] in ("gram_altin", "dolar"))
    return {"assets": assets, "prices": prices, "band": band, "status": "ok" if core_ok else "güncellenmedi"}


# ---------------------------------------------------------------- TCMB banknote spread (calculator reference)
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"


def parse_tcmb(xml_bytes):
    """USD banknote buying/selling from TCMB today.xml -> {alis, satis, pct, tarih}. Public data (TCMB)."""
    import xml.etree.ElementTree as ET
    if b"<!DOCTYPE" in xml_bytes[:2000] or b"<!ENTITY" in xml_bytes:
        raise ValueError("DTD not allowed")
    root = ET.fromstring(xml_bytes)
    m, d, y = root.attrib["Date"].split("/")
    for c in root.findall("Currency"):
        if c.attrib.get("CurrencyCode") == "USD":
            buy, sell = float(c.findtext("BanknoteBuying")), float(c.findtext("BanknoteSelling"))
            if not (0 < buy <= sell):
                raise ValueError("bad rates")
            return {"alis": round(buy, 4), "satis": round(sell, 4), "pct": round((sell - buy) / sell * 100, 2),
                    "tarih": f"{y}-{int(m):02d}-{int(d):02d}", "kaynak": "TCMB efektif kurlar (today.xml)"}
    raise ValueError("USD not found")


def tcmb_ref(previous=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(TCMB_URL, headers=UA), timeout=30) as r:
            data = r.read(500_000)
        ref = parse_tcmb(data)
        status["TCMB_USD"] = f"OK {ref['tarih']} %{ref['pct']}"
        return {"usd": ref}
    except Exception as e:
        status["TCMB_USD"] = f"ERR {type(e).__name__}: {str(e)[:80]}"
        return previous          # keep the last good reference (it carries its own date)


# ---------------------------------------------------------------- compare.json (Karşılaştır sayfası)
COMPARE_DAYS = 740          # ~2 years of calendar days
# id, label, unit, kind ("fiyat": real level published; "endeks": rebased to 100 at the first day)
COMPARE = [("gram_altin", "Gram altın", "TL"), ("gram_gumus", "Gram gümüş", "TL"),
           ("ons_altin", "Ons altın", "$"), ("ons_gumus", "Ons gümüş", "$"), ("dolar", "Dolar/TL", "TL"),
           ("brent", "Brent petrol", "$"), ("wti", "WTI petrol", "$"), ("btc", "Bitcoin", "$"), ("eth", "Ether", "$"),
           ("bist100_tl", "BIST 100 (TL)", None), ("bist100_usd", "BIST 100 (dolar bazında)", None),
           ("spy", "S&P 500 fonu (SPY)", None), ("qqq", "Nasdaq 100 fonu (QQQ)", None)]


def sig(v, n=5):
    if v == 0:
        return 0
    from math import floor, log10
    return round(v, max(0, n - 1 - int(floor(log10(abs(v))))))


def compare_series(data, today):
    """Union-of-dates table. Licensed index levels (BIST 100) and fund prices are rebased to 100."""
    usd, gold, silver, xu = (data.get(k) or {} for k in ("USDTRY", "GOLD_USD", "SILVER_USD", "XU100"))
    src = {"gram_altin": combine(gold, usd, lambda g, u: g * u / OZ_GRAM) if gold and usd else {},
           "gram_gumus": combine(silver, usd, lambda s, u: s * u / OZ_GRAM) if silver and usd else {},
           "ons_altin": gold, "ons_gumus": silver, "dolar": usd,
           "brent": data.get("BRENT_USD") or {}, "wti": data.get("WTI_USD") or {},
           "btc": data.get("BTC_USD") or {}, "eth": data.get("ETH_USD") or {},
           "bist100_tl": xu, "bist100_usd": combine(xu, usd, lambda x, u: x / u) if xu and usd else {},
           "spy": data.get("SPY") or {}, "qqq": data.get("QQQ") or {}}
    cut = (dt.date.fromisoformat(today) - dt.timedelta(days=COMPARE_DAYS)).isoformat()
    tdy = dt.date.fromisoformat(today).isoformat()
    keep = {k: {d: v for d, v in s.items() if cut <= d < tdy} for k, s in src.items()}
    dates = sorted(set(d for s in keep.values() for d in s))
    assets = []
    for aid, label, unit in COMPARE:
        s = keep.get(aid) or {}
        if len(s) < 20:
            continue
        first = s[min(s)]
        vals = [None if d not in s else sig(s[d] if unit else s[d] / first * 100) for d in dates]
        assets.append({"id": aid, "label": label, "unit": unit or "endeks, ilk gün = 100",
                       "kind": "fiyat" if unit else "endeks", "asof": max(s), "v": vals})
    return {"dates": dates, "assets": assets}


def main():
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    data = update_raw()
    for k, v in status.items():
        print(f"  {k}: {v}")
    d = derive(data, now.date().isoformat(), crypto_refs(NOTEBOOK))
    prev = None
    try:
        prev = json.load(open(os.path.join(SITE_OUT, "tl.json"), encoding="utf-8")).get("makas_ref")
    except Exception:
        pass
    ref = tcmb_ref(prev)
    if ref:
        d["makas_ref"] = ref
    rec = {"schema": "phd.tl/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
           "generated_at": now.isoformat().replace("+00:00", "Z"), "attribution": ATTRIBUTION,
           "license": "Yalnızca görüntüleme (atıfla). Girdiler Yahoo Finance/OKX kişisel kullanım şartlı; CC BY 4.0 kapsamında değil. Ayrıntı: veri.html", "note": DATA_NOTE, "rules_version": "v1",
           "inputs": {k: ("ok" if v.startswith("OK") else "hata") for k, v in status.items()}, **d}
    os.makedirs(SITE_OUT, exist_ok=True)
    path = os.path.join(SITE_OUT, "tl.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    print(f"tl.json: {d['status']}, {len(d['assets'])} varlık")
    try:
        c = compare_series(data, now.date().isoformat())
        crec = {"schema": "phd.compare/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
                "generated_at": rec["generated_at"], "attribution": ATTRIBUTION, "license": rec["license"],
                "note": "Günlük kapanışlar, son ~2 yıl. BIST 100 ve fonlar yalnız 100'e endeksli seri olarak "
                        "yayımlanır (seviye değil). Girdi kaynağı Yahoo Finance (kişisel kullanım şartlı).",
                "disclaimer": "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır.", **c}
        cp = os.path.join(SITE_OUT, "compare.json")
        with open(cp + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(crec, fh, ensure_ascii=False, separators=(",", ":"))
        os.replace(cp + ".tmp", cp)
        print(f"compare.json: {len(c['assets'])} varlık, {len(c['dates'])} gün")
    except Exception as e:      # never break tl.json
        print(f"compare.json failed: {type(e).__name__}: {e}")
    if not any(v.startswith("OK") for v in status.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
