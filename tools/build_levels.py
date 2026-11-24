"""Piyasa Hava Durumu — "Destek ve direnç" + "Zincir" (B6). Private engine; output is derived only.

Writes data/site/seviyeler.json (and the small home-page excerpt data/site/zincir.json):
  * per asset, price zones where the daily close turned more than once in the last ~2 years
    (rule-based swing points, clustered), split into zones above (direnç) and below (destek) the
    last close, with how many times price turned there and when it last did;
  * what happened at those zones in the last 10 sessions, in plain past-tense sentences
    ("… bölgesine yaklaştı ve geri döndü: direnç oldu", "… bölgesinin üstüne çıktı");
  * "Zincir": petrol → dolar → ABD 10 yıllık faiz → altın → borsa → bitcoin, read as one chain.
Factual, past tense, no forecasts, no action words.

Licensing: levels are published as prices only for assets already shown as prices on the site
(metals, oil, USD/TRY, BTC, ETH) and for the 10-year Treasury yield (FRED DGS10, public domain).
Fund/index assets (UUP, SPY, QQQ, BIST 100) are published only as % distance from the last close
and as a series rebased to 100 — never as levels.

Method (also in plain words on yontem.html):
  swing point  = a close that is the highest (or lowest) of the 5 sessions on each side
  zone         = swing points (highs and lows together) whose prices are within a tolerance band;
                 tolerance = 2 × median absolute daily move of the last 120 sessions, 0.4 %…4 %
  zone price   = mean of its swing points; a zone needs ≥ 2 swing points
  direnç/destek= zone above / below the last close (± half a tolerance = "fiyat bu bölgede")
  events (10 sessions): a close inside a zone, then price back on the side it came from by more
    than one tolerance → "direnç oldu" / "destek oldu"; the last two closes on the other side of
    a zone it was on 10 sessions ago → "üstüne çıktı" / "altına indi".

Inputs (data-feed, private side): data/research/tl_1d/<NAME>.csv (date,close; fetch_tl.py),
US10Y.csv (FRED DGS10, fetched and stored here).
"""
import csv, datetime as dt, json, math, os, statistics, sys, urllib.request

FEED = os.environ.get("FEED_DIR", "data")
SITE_OUT = os.environ.get("SITE_OUT", os.path.join(FEED, "site"))
TL_DIR = os.environ.get("TL_RAW_DIR", os.path.join(FEED, "research", "tl_1d"))
OZ = 31.1035
LOOKBACK = 504          # sessions (~2 years) searched for swing points
PIVOT_K = 5             # sessions on each side
EVENT_N = 10            # sessions checked for events
SERIES_N = 260          # sessions sent for the chart (~1 year)
MAX_EACH = 3            # zones shown on each side
STALE_DAYS = 7
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri, CC BY 4.0"
UA = {"User-Agent": "Mozilla/5.0 (piyasa-hava-durumu; github actions)"}

# id, label, label_en, unit, abs (levels as prices?), decimals, source
ASSETS = [
    ("brent", "Brent petrol", "Brent oil", "$", True, 2, "BRENT_USD"),
    ("dolar_fonu", "Dolar (UUP fonu)", "US dollar (UUP fund)", "", False, 2, "UUP"),
    ("abd10y", "ABD 10 yıllık faiz", "US 10-year yield", "%", True, 2, "US10Y"),
    ("ons_altin", "Ons altın", "Gold (ounce)", "$", True, 0, "GOLD_USD"),
    ("gram_altin", "Gram altın", "Gold (gram)", "TL", True, 0, "gram:GOLD_USD"),
    ("ons_gumus", "Ons gümüş", "Silver (ounce)", "$", True, 2, "SILVER_USD"),
    ("gram_gumus", "Gram gümüş", "Silver (gram)", "TL", True, 2, "gram:SILVER_USD"),
    ("dolar", "Dolar/TL", "USD/TRY", "TL", True, 3, "USDTRY"),
    ("spy", "S&P 500 fonu (SPY)", "S&P 500 fund (SPY)", "", False, 2, "SPY"),
    ("qqq", "Nasdaq 100 fonu (QQQ)", "Nasdaq 100 fund (QQQ)", "", False, 2, "QQQ"),
    ("bist100", "BIST 100", "BIST 100", "", False, 0, "XU100"),
    ("btc", "Bitcoin", "Bitcoin", "$", True, 0, "BTC_USD"),
    ("eth", "Ethereum", "Ethereum", "$", True, 0, "ETH_USD"),
]
CHAIN = [
    ("brent", "Petrol", "Oil"),
    ("dolar_fonu", "Dolar", "Dollar"),
    ("abd10y", "ABD faizi", "US yields"),
    ("ons_altin", "Altın", "Gold"),
    ("spy", "Borsa (ABD)", "Stocks (US)"),
    ("btc", "Bitcoin", "Bitcoin"),
]
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
status = {}


# ---------------------------------------------------------------- inputs (private side)
def read_csv(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                v = float(r["close"])
            except (KeyError, TypeError, ValueError):
                continue
            if v > 0 and r.get("date"):
                out[r["date"][:10]] = v
    return out


def write_csv(path, series):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "close"])
        for d in sorted(series):
            w.writerow([d, f"{series[d]:.6f}"])
    os.replace(path + ".tmp", path)


def parse_fred(txt):
    out = {}
    for line in txt.splitlines()[1:]:
        parts = line.strip().split(",")
        if len(parts) != 2 or not parts[0][:4].isdigit():
            continue
        try:
            v = float(parts[1])
        except ValueError:
            continue          # "." = holiday
        if v > 0:
            out[parts[0][:10]] = v
    return out


def update_us10y():
    """FRED DGS10 (10-year Treasury constant maturity, Federal Reserve H.15; public domain)."""
    path = os.path.join(TL_DIR, "US10Y.csv")
    old = read_csv(path)
    start = (dt.date.today() - dt.timedelta(days=60)).isoformat() if len(old) > 400 else "2015-01-01"
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd={start}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            new = parse_fred(r.read().decode("utf-8", "replace"))
        if not new:
            raise RuntimeError("empty")
        old.update(new)
        write_csv(path, old)
        status["US10Y"] = f"OK DGS10 +{len(new)} -> {len(old)}"
    except Exception as e:
        status["US10Y"] = f"ERR DGS10 {type(e).__name__}: {str(e)[:100]}"
    return old


def load_series(src, raw):
    if src.startswith("gram:"):
        oz, fx = raw.get(src[5:]) or {}, raw.get("USDTRY") or {}
        return {d: oz[d] * fx[d] / OZ for d in oz if d in fx}
    return raw.get(src) or {}


# ---------------------------------------------------------------- engine
def tolerance(closes):
    tail = closes[-121:]
    moves = [abs(math.log(b / a)) for a, b in zip(tail, tail[1:]) if a > 0 and b > 0]
    if not moves:
        return 0.01
    return min(0.04, max(0.004, 2 * statistics.median(moves)))


def swings(closes, k=PIVOT_K):
    """Indexes of confirmed swing highs and lows (ties: first index only)."""
    out = []
    for i in range(k, len(closes) - k):
        win = closes[i - k:i + k + 1]
        c = closes[i]
        if c == max(win) and win.index(c) == k:
            out.append((i, "tepe"))
        elif c == min(win) and win.index(c) == k:
            out.append((i, "dip"))
    return out


def zones(dates, closes, tol):
    pts = sorted(((closes[i], i, kind) for i, kind in swings(closes)), key=lambda x: x[0])
    groups = []
    for p in pts:
        if groups and abs(p[0] / statistics.mean(x[0] for x in groups[-1]) - 1) <= tol:
            groups[-1].append(p)
        else:
            groups.append([p])
    out = []
    for g in groups:
        if len(g) < 2:
            continue
        idx = sorted(x[1] for x in g)
        out.append({"price": statistics.mean(x[0] for x in g), "touches": len(g),
                    "first": dates[idx[0]], "last": dates[idx[-1]], "last_i": idx[-1]})
    return out


def side(c, level, tol):
    r = c / level - 1
    return 1 if r > tol else -1 if r < -tol else 0


def events(dates, closes, zs, tol, n=EVENT_N):
    """Past-tense observations in the last n sessions. Each zone gives at most one event."""
    out = []
    if len(closes) < n + 2:
        return out
    last = closes[-1]
    for z in zs:
        L = z["price"]
        before = side(closes[-n - 1], L, tol)
        now = side(last, L, tol)
        recent = closes[-n:]
        touched = [j for j, c in enumerate(recent) if abs(c / L - 1) <= tol]
        if before != 0 and now == before and touched:
            j = len(closes) - n + touched[-1]
            if j < len(closes) - 1:
                out.append({"date": dates[j], "kind": "direnc_oldu" if before < 0 else "destek_oldu", "zone": L})
        elif before != 0 and now == -before and side(closes[-2], L, tol) == now:
            j = len(closes) - 1          # first close of the run that ended on the new side
            while j > len(closes) - n and side(closes[j - 1], L, tol) != before:
                j -= 1
            out.append({"date": dates[j], "kind": "ustune_cikti" if now > 0 else "altina_indi", "zone": L})
    out.sort(key=lambda e: e["date"], reverse=True)
    return out


def pct(a, b):
    return None if not a or not b else round((a / b - 1) * 100, 2)


def analyse(series):
    """series: {date: close}. Returns the engine result with raw prices (private)."""
    ds = sorted(series)[-LOOKBACK:]
    cs = [series[d] for d in ds]
    if len(cs) < 60:
        return None
    tol = tolerance(cs)
    zs = zones(ds, cs, tol)
    last = cs[-1]
    above = sorted((z for z in zs if side(last, z["price"], tol / 2) < 0), key=lambda z: z["price"])[:MAX_EACH]
    below = sorted((z for z in zs if side(last, z["price"], tol / 2) > 0), key=lambda z: -z["price"])[:MAX_EACH]
    at = [z for z in zs if side(last, z["price"], tol / 2) == 0]
    yr = cs[-252:]
    return {"dates": ds, "closes": cs, "tol": tol, "last": last, "asof": ds[-1],
            "above": above, "below": below, "at": max(at, key=lambda z: z["touches"]) if at else None,
            "events": events(ds, cs, zs, tol),
            "chg1": pct(cs[-1], cs[-2]), "chg20": pct(cs[-1], cs[-21] if len(cs) > 20 else cs[0]),
            "hi52": max(yr), "lo52": min(yr)}


# ---------------------------------------------------------------- public sentences
def fnum(v, nd, en=False):
    s = f"{v:,.{nd}f}"
    return s if en else s.replace(",", "X").replace(".", ",").replace("X", ".")


def fpct(v, en=False):
    sg = "+" if v > 0 else "−" if v < 0 else ""
    a = fnum(abs(v), 1, en)
    return f"{sg}{a}%" if en else f"{sg}%{a}"


def trday(iso, en=False):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS_EN[m - 1]}" if en else f"{d} {MONTHS[m - 1]}"


def zone_txt(price, last, unit, nd, absolute, en=False):
    """Short label for a zone in the lists: a price, or the % distance for fund/index assets."""
    if absolute:
        if unit == "%":
            return f"{fnum(price, nd, en)}%" if en else f"%{fnum(price, nd, en)}"
        return fnum(price, nd, en) + {"$": " $", "TL": " TL"}.get(unit, "")
    d = pct(price, last)
    a = fnum(abs(d), 1, en)
    if en:
        return f"{a}% {'above' if d > 0 else 'below'}"
    return f"%{a} {'yukarıda' if d > 0 else 'aşağıda'}"


def zone_forms(price, last, unit, nd, absolute, en=False):
    """(dative, genitive) noun phrases for event sentences."""
    if absolute:
        v = zone_txt(price, last, unit, nd, absolute, en)
        return (f"the {v} zone", f"the {v} zone") if en else (f"{v} bölgesine", f"{v} bölgesinin")
    d = pct(price, last)
    a = fnum(abs(d), 1, en)
    if en:
        w = f"the zone {a}% {'above' if d > 0 else 'below'} the last close"
        return w, w
    w = "üstündeki" if d > 0 else "altındaki"
    return f"son kapanışın %{a} {w} bölgeye", f"son kapanışın %{a} {w} bölgenin"


EVENT_TR = {"direnc_oldu": "{d}: {dat} yaklaştı ve geri döndü — direnç oldu.",
            "destek_oldu": "{d}: {dat} indi ve geri döndü — destek oldu.",
            "ustune_cikti": "{d}: {gen} üstüne çıktı; son iki kapanış bölgenin üstünde.",
            "altina_indi": "{d}: {gen} altına indi; son iki kapanış bölgenin altında."}
EVENT_EN = {"direnc_oldu": "{d}: neared {dat} and turned back — it acted as resistance.",
            "destek_oldu": "{d}: fell to {dat} and turned back — it acted as support.",
            "ustune_cikti": "{d}: moved above {gen}; the last two closes are above it.",
            "altina_indi": "{d}: moved below {gen}; the last two closes are below it."}


def direction(v, en=False):
    if v is None:
        return "—"
    if abs(v) < 0.2:
        return "flat" if en else "yatay"
    return ("up" if v > 0 else "down") if en else ("yükseldi" if v > 0 else "düştü")


def public(spec, res, today):
    aid, label, label_en, unit, absolute, nd, _ = spec
    last = res["last"]

    def z(zz):
        o = {"dist_pct": pct(zz["price"], last), "touches": zz["touches"], "last": zz["last"]}
        if absolute:
            o["p"] = round(zz["price"], nd)
        o["text"] = zone_txt(zz["price"], last, unit, nd, absolute)
        o["text_en"] = zone_txt(zz["price"], last, unit, nd, absolute, True)
        return o

    evs = []
    for e in res["events"][:3]:
        ft, fe = zone_forms(e["zone"], last, unit, nd, absolute), zone_forms(e["zone"], last, unit, nd, absolute, True)
        evs.append({"date": e["date"], "kind": e["kind"],
                    "text": EVENT_TR[e["kind"]].format(d=trday(e["date"]), dat=ft[0], gen=ft[1]),
                    "text_en": EVENT_EN[e["kind"]].format(d=trday(e["date"], True), dat=fe[0], gen=fe[1])})
    ds, cs = res["dates"][-SERIES_N:], res["closes"][-SERIES_N:]
    if absolute:
        series = [[d, round(c, nd if nd > 0 else 0)] for d, c in zip(ds, cs)]
    else:
        series = [[d, round(c / cs[0] * 100, 2)] for d, c in zip(ds, cs)]
    age = (today - dt.date.fromisoformat(res["asof"])).days
    o = {"id": aid, "label": label, "label_en": label_en, "unit": unit if absolute else "", "abs": absolute,
         "nd": nd, "asof": res["asof"], "eski": age > STALE_DAYS,
         "chg1d_pct": res["chg1"], "chg20d_pct": res["chg20"],
         "direnc": [z(x) for x in res["above"]], "destek": [z(x) for x in res["below"]],
         "bolgede": z(res["at"]) if res["at"] else None,
         "hi52_dist_pct": pct(res["hi52"], last), "lo52_dist_pct": pct(res["lo52"], last),
         "tol_pct": round(res["tol"] * 100, 2),
         "events": evs, "series": series,
         "series_kind": "fiyat" if absolute else "endeks, ilk gün = 100"}
    if absolute:
        o["close"] = round(last, nd)
        o["hi52"], o["lo52"] = round(res["hi52"], nd), round(res["lo52"], nd)
    return o


def chain_link(a, tr, en):
    """One plain sentence per chain link (numbers from code)."""
    if not a:
        return None
    c20 = a["chg20d_pct"]
    if a["bolgede"]:
        near_tr = f"fiyat şu an bir destek/direnç bölgesinde ({a['bolgede']['text']})"
        near_en = f"price is at a support/resistance zone now ({a['bolgede']['text_en']})"
    else:
        up, dn = (a["direnc"][0] if a["direnc"] else None), (a["destek"][0] if a["destek"] else None)
        near_tr = "; ".join(t for t in [
            f"en yakın direnç %{fnum(abs(up['dist_pct']), 1)} yukarıda" if up else None,
            f"en yakın destek %{fnum(abs(dn['dist_pct']), 1)} aşağıda" if dn else None] if t) or "yakında bölge yok"
        near_en = "; ".join(t for t in [
            f"nearest resistance {fnum(abs(up['dist_pct']), 1, True)}% above" if up else None,
            f"nearest support {fnum(abs(dn['dist_pct']), 1, True)}% below" if dn else None] if t) or "no zone nearby"
    s_tr = f"{tr}: 20 günde {fpct(c20)} ({direction(c20)}); {near_tr}." if c20 is not None else f"{tr}: veri yok."
    s_en = f"{en}: {fpct(c20, True)} over 20 days ({direction(c20, True)}); {near_en}." if c20 is not None else f"{en}: no data."
    ev = a["events"][0] if a["events"] else None
    return {"id": a["id"], "ad": tr, "ad_en": en, "chg20d_pct": c20, "yon": direction(c20), "yon_en": direction(c20, True),
            "text": s_tr, "text_en": s_en, "yakin": near_tr, "yakin_en": near_en, "son_olay": ev["text"] if ev else None, "son_olay_en": ev["text_en"] if ev else None}


def build(raw, today=None):
    today = today or dt.date.today()
    out, missing = [], []
    for spec in ASSETS:
        res = analyse(load_series(spec[6], raw))
        if not res:
            missing.append(spec[0])
            continue
        out.append(public(spec, res, today))
    by = {a["id"]: a for a in out}
    chain = [x for x in (chain_link(by.get(i), tr, en) for i, tr, en in CHAIN) if x]
    dates = [a["asof"] for a in out]
    return {
        "schema": "phd.seviyeler/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_date": max(dates) if dates else None, "attribution": ATTRIBUTION,
        "license": "CC BY 4.0 (yalnız kamu kaynaklı türetilmiş alanlar; fon/endeks varlıkları yalnız % uzaklık ve 100'e endeksli seri)",
        "method": ("Destek/direnç bölgesi: son ~2 yılda günlük kapanışın en az iki kez döndüğü fiyat bölgesi "
                   "(5 gün öncesine ve sonrasına göre en yüksek/en düşük kapanışlar, oynaklığa göre genişlik). "
                   "Geçmişi anlatır; gelecekte çalışacağını söylemez."),
        "chain_note": ("Okuma sırası: petrol → dolar → ABD faizi → altın → borsa → bitcoin. Para genelde bu halkalar "
                       "üzerinden yer değiştirir; halkalar birlikte okunur. Kesin bir kural değildir."),
        "chain_note_en": ("Reading order: oil → dollar → US yields → gold → stocks → bitcoin. Money tends to move along "
                          "these links; read them together. It is not a fixed rule."),
        "disclaimer": "Yatırım tavsiyesi değildir. Geçmiş fiyat bölgeleri bilgi amaçlıdır.",
        "chain": chain, "assets": out, "missing": missing, "status": status,
    }


def main():
    raw = {}
    for spec in ASSETS:
        src = spec[6].split(":")[-1]
        if src != "US10Y":
            raw[src] = read_csv(os.path.join(TL_DIR, src + ".csv"))
    raw.setdefault("USDTRY", read_csv(os.path.join(TL_DIR, "USDTRY.csv")))
    raw["US10Y"] = update_us10y()
    rec = build(raw)
    os.makedirs(SITE_OUT, exist_ok=True)
    path = os.path.join(SITE_OUT, "seviyeler.json")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    small = {k: rec[k] for k in ("schema", "schema_version", "source", "site_url", "generated_at", "data_date",
                                 "attribution", "license", "chain_note", "chain_note_en", "disclaimer", "chain")}
    small["schema"] = "phd.zincir/1"
    zp = os.path.join(SITE_OUT, "zincir.json")
    with open(zp + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(small, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(zp + ".tmp", zp)
    print("seviyeler.json:", rec["data_date"], "assets", len(rec["assets"]), "missing", ",".join(rec["missing"]) or "-",
          "|", "; ".join(f"{k} {v}" for k, v in status.items()))


if __name__ == "__main__":
    main()
