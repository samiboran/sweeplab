"""Builds the daily dataset behind the Kaldıraç Gözlem Defteri, in four layers.

  Rejim        BTC/ETH trend vs 50/200-day averages (1y of OKX daily closes),
               net liquidity (WALCL − WTREGEN − RRPONTSYD, weekly), 10y real yield
               (DFII10), DXY (Yahoo DX-Y.NYB; FRED broad dollar DTWEXBGS as fallback),
               stablecoin supply (DefiLlama)
  Risk iştahı  S&P 500, Nasdaq Composite, VIX, US high-yield OAS (BAMLH0A0HYM2)
  Pozisyon     OKX BTC/ETH perp: OI, funding, L/S ratio, taker flow, price, and a
               daily "what happened" label from price vs OI direction
               (from okx_history_raw.json) + CFTC COT for CME Bitcoin/Ether futures
  Altın & Makro gold (COMEX futures; XAUT/PAXG fallback), CFTC managed-money net in
               gold (weekly), GLD holdings (tonnes), WTI and Brent
  Korelasyon   30/7-day correlation of daily returns: BTC vs S&P, Nasdaq, DXY, ETH,
               gold; ETH vs gold
  Takvim       FOMC decision days, CPI and NFP release days

Weekly or market-day series are carried forward to calendar days; each carried
value keeps the date it is from (`*_asof`). Output: data/derivs/notebook_daily.csv
(one row per date) and notebook_daily.json (same rows, nested by layer).
Run fetch_okx_history.py (DAYS>=90) first.
"""
import csv, datetime as dt, io, json, math, os, time, urllib.parse, urllib.request

OUT = os.environ.get("OUT_DIR", "data/derivs")
SHOW_DAYS = int(os.environ.get("SHOW_DAYS", "30"))
LOOKBACK = 140  # history fetched, enough for 30d correlations and weekly series
UA = {"User-Agent": "Mozilla/5.0 (derivs-notebook; github actions)"}

# Release calendars: BLS 2026 schedule (CPI, Employment Situation) and the Fed's
# 2026 FOMC calendar (decision day = second day of the meeting).
CALENDAR = {
    "FOMC": ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
             "2026-09-16", "2026-10-28", "2026-12-09"],
    "CPI": ["2026-01-13", "2026-02-13", "2026-03-11", "2026-04-10", "2026-05-12", "2026-06-10",
            "2026-07-14", "2026-08-12", "2026-09-11", "2026-10-14", "2026-11-10", "2026-12-10"],
    "NFP": ["2026-06-05", "2026-07-02", "2026-08-07", "2026-09-04", "2026-10-02",
            "2026-11-06", "2026-12-04"],
}

status = {}


def fetch(url, kind="json", tries=3, encoding="utf-8"):
    err = None
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                body = r.read()
            return json.loads(body) if kind == "json" else body.decode(encoding, errors="replace")
        except Exception as e:
            err = str(e)[:200]
            time.sleep(2 * (a + 1))
    raise RuntimeError(err)


def fred(series, start):
    """{date: float} from FRED's public CSV download (no API key)."""
    try:
        txt = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}", "text")
        out = {}
        for row in csv.reader(io.StringIO(txt)):
            if len(row) == 2 and row[0][:2] == "20" and row[1] not in (".", ""):
                out[row[0]] = float(row[1])
        status[series] = f"OK {len(out)} ({min(out)}..{max(out)})" if out else "EMPTY"
        return out
    except Exception as e:
        status[series] = "ERR " + str(e)
        return {}


def yahoo(symbol):
    try:
        j = fetch(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=1y&interval=1d")
        res = j["chart"]["result"][0]
        out = {}
        for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
            if c is not None:
                out[dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")] = float(c)
        status["yahoo:" + symbol] = f"OK {len(out)}"
        return out
    except Exception as e:
        status["yahoo:" + symbol] = "ERR " + str(e)
        return {}


def stablecoins(start):
    try:
        j = fetch("https://stablecoins.llama.fi/stablecoincharts/all")
        out = {}
        for x in j:
            d = dt.datetime.fromtimestamp(int(x["date"]), dt.timezone.utc).strftime("%Y-%m-%d")
            if d >= start:
                v = (x.get("totalCirculatingUSD") or {}).get("peggedUSD")
                if v:
                    out[d] = float(v)
        status["defillama_stables"] = f"OK {len(out)}"
        return out
    except Exception as e:
        status["defillama_stables"] = "ERR " + str(e)
        return {}


def cot(code, label):
    """CFTC Traders in Financial Futures (futures only) for one CME contract."""
    q = urllib.parse.urlencode({"$where": f"cftc_contract_market_code='{code}'",
                                "$order": "report_date_as_yyyy_mm_dd DESC", "$limit": "30"})
    try:
        rows = fetch("https://publicreporting.cftc.gov/resource/gpe5-46if.json?" + q)
        out = {}
        for r in rows:
            d = r["report_date_as_yyyy_mm_dd"][:10]
            f = lambda k: float(r.get(k) or 0)
            out[d] = {
                "oi": f("open_interest_all"),
                "lev_net": f("lev_money_positions_long") - f("lev_money_positions_short"),
                "am_net": f("asset_mgr_positions_long") - f("asset_mgr_positions_short"),
                "dealer_net": f("dealer_positions_long_all") - f("dealer_positions_short_all"),
            }
        status["cot_" + label] = f"OK {len(out)} ({min(out) if out else ''}..{max(out) if out else ''})"
        return out
    except Exception as e:
        status["cot_" + label] = "ERR " + str(e)
        return {}


def cot_gold():
    """CFTC disaggregated futures-only report, COMEX gold (088691): managed money."""
    q = urllib.parse.urlencode({"$where": "cftc_contract_market_code='088691'",
                                "$order": "report_date_as_yyyy_mm_dd DESC", "$limit": "30"})
    try:
        rows = fetch("https://publicreporting.cftc.gov/resource/72hh-3qpy.json?" + q)
        out = {}
        for r in rows:
            f = lambda k: float(r.get(k) or 0)
            out[r["report_date_as_yyyy_mm_dd"][:10]] = {
                "mm_long": f("m_money_positions_long_all"), "mm_short": f("m_money_positions_short_all"),
                "mm_net": f("m_money_positions_long_all") - f("m_money_positions_short_all"),
                "oi": f("open_interest_all"),
            }
        status["cot_gold"] = f"OK {len(out)} ({min(out) if out else ''}..{max(out) if out else ''})"
        return out
    except Exception as e:
        status["cot_gold"] = "ERR " + str(e)
        return {}


def okx_spot_daily(inst):
    """Daily closes of an OKX spot pair (gold-backed tokens as a gold fallback)."""
    try:
        j = fetch(f"https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar=1Dutc&limit=100")
        out = {dt.datetime.fromtimestamp(int(c[0]) / 1000, dt.timezone.utc).strftime("%Y-%m-%d"): float(c[4])
               for c in j["data"] if len(c) < 9 or c[8] == "1"}
        status["okx:" + inst] = f"OK {len(out)}"
        return out
    except Exception as e:
        status["okx:" + inst] = "ERR " + str(e)
        return {}


def gld_tonnes():
    """SPDR Gold Shares (GLD) daily holdings in tonnes, from SPDR's public archive CSV."""
    try:
        txt = fetch("https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv", "text", encoding="latin-1")
        rows = list(csv.reader(txt.replace("\r", "\n").splitlines()))
        hi = next(i for i, r in enumerate(rows) if any("Tonnes" in c for c in r))
        head = [c.strip() for c in rows[hi]]
        col = next(i for i, c in enumerate(head) if "Tonnes" in c)
        out = {}
        for r in rows[hi + 1:]:
            if len(r) <= col:
                continue
            try:
                d = dt.datetime.strptime(r[0].strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
                out[d] = float(r[col].replace(",", ""))
            except ValueError:
                continue
        status["gld_tonnes"] = f"OK {len(out)} ({min(out)}..{max(out)})" if out else "EMPTY"
        return out
    except Exception as e:
        status["gld_tonnes"] = "ERR " + str(e)
        return {}


def asof(series, day):
    """Latest observation on or before `day` -> (value, date) or (None, None)."""
    best = None
    for d in series:
        if d <= day and (best is None or d > best):
            best = d
    return (series[best], best) if best else (None, None)


def pct(a, b):
    return (a / b - 1) * 100 if a is not None and b else None


def corr(xs, ys, min_n=10):
    n = len(xs)
    if n < min_n:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def window_corr(a, b, end, days=30, min_n=10):
    """Correlation of returns between consecutive dates both series share, within
    the trailing `days` calendar days ending at `end` (S&P has no weekends, so BTC
    is sampled on S&P's trading dates)."""
    start = (dt.date.fromisoformat(end) - dt.timedelta(days=days + 7)).isoformat()
    common = sorted(d for d in a if d in b and start <= d <= end)
    pairs = [(math.log(a[d1] / a[d0]), math.log(b[d1] / b[d0]))
             for d0, d1 in zip(common, common[1:])
             if d1 >= (dt.date.fromisoformat(end) - dt.timedelta(days=days)).isoformat()]
    if not pairs:
        return None, 0
    c = corr([p[0] for p in pairs], [p[1] for p in pairs], min_n)
    return c, len(pairs)


def sma(closes, day, n):
    """Simple moving average of the n daily closes ending on `day` (None if short)."""
    ds = sorted(d for d in closes if d <= day)[-n:]
    if len(ds) < n:
        return None
    return sum(closes[d] for d in ds) / n


def trend(closes, day):
    """Boğa: close > MA200 and MA50 > MA200. Ayı: close < MA200 and MA50 < MA200.
    Otherwise Geçiş (mixed signals)."""
    c = closes.get(day)
    m50, m200 = sma(closes, day, 50), sma(closes, day, 200)
    if c is None or m50 is None or m200 is None:
        return {"state": None, "close": c, "ma50": m50, "ma200": m200}
    if c > m200 and m50 > m200:
        st = "boga"
    elif c < m200 and m50 < m200:
        st = "ayi"
    else:
        st = "gecis"
    return {"state": st, "close": c, "ma50": round(m50, 2), "ma200": round(m200, 2),
            "dist200_pct": round((c / m200 - 1) * 100, 2), "dist50_pct": round((c / m50 - 1) * 100, 2)}


PRICE_DEAD, OI_DEAD = 0.5, 1.0  # % moves smaller than this count as flat


def flow_label(price_chg, oi_chg):
    """What price and open interest did together on the day. `oi_chg` is the
    change in coin-denominated OI: USD OI falls with price on its own and would
    make every red day look like a long washout."""
    if price_chg is None or oi_chg is None:
        return None
    if abs(price_chg) < PRICE_DEAD:
        return "yatay"
    if abs(oi_chg) < OI_DEAD:
        return "oi_sabit"  # price moved, positions did not: no new leverage, none flushed
    if price_chg > 0:
        return "kaldiracli_yukselis" if oi_chg > 0 else "short_squeeze"
    return "yeni_short" if oi_chg > 0 else "temizlik"


def okx_rows():
    import importlib.util
    spec = importlib.util.spec_from_file_location("h", os.path.join(os.path.dirname(__file__), "fetch_okx_history.py"))
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    raw = json.load(open(f"{OUT}/okx_history_raw.json"))
    return {c.lower(): h.build(raw, c)[0] for c in ("BTC", "ETH")}


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    start = (today - dt.timedelta(days=LOOKBACK)).isoformat()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(SHOW_DAYS, 0, -1)]

    walcl, tga, rrp = fred("WALCL", start), fred("WTREGEN", start), fred("RRPONTSYD", start)
    real10, dxy_broad = fred("DFII10", start), fred("DTWEXBGS", start)
    spx, ndx, vix, hy = fred("SP500", start), fred("NASDAQCOM", start), fred("VIXCLS", start), fred("BAMLH0A0HYM2", start)
    dxy = yahoo("DX-Y.NYB")
    dxy_src = "DXY (ICE)" if dxy else "Broad dollar (FRED DTWEXBGS)"
    if not dxy:
        dxy = dxy_broad
    stables = stablecoins(start)
    cot_btc, cot_eth = cot("133741", "btc"), cot("146021", "eth")
    gold, gold_src = yahoo("GC=F"), "Altın vadeli (COMEX, GC=F)"
    if not gold:
        gold, gold_src = okx_spot_daily("XAUT-USDT"), "XAUT (OKX)"
    if not gold:
        gold, gold_src = okx_spot_daily("PAXG-USDT"), "PAXG (OKX)"
    wti, brent = yahoo("CL=F"), yahoo("BZ=F")
    if not wti:
        wti = fred("DCOILWTICO", start)
    if not brent:
        brent = fred("DCOILBRENTEU", start)
    cotg, gld = cot_gold(), gld_tonnes()

    # Net liquidity, weekly on the Fed balance-sheet Wednesday, USD millions.
    # WALCL and WTREGEN are in millions, RRPONTSYD in billions.
    netliq = {}
    for d, v in walcl.items():
        t, _ = asof(tga, d)
        r, _ = asof(rrp, d)
        if t is not None and r is not None:
            netliq[d] = v - t - r * 1000
    status["net_liquidity"] = f"OK {len(netliq)} weeks" if netliq else "EMPTY"

    okx = okx_rows()
    btc_close = {d: r["close"] for d, r in okx["btc"].items() if "close" in r}
    eth_close = {d: r["close"] for d, r in okx["eth"].items() if "close" in r}

    def change(series, day, back):
        v, d = asof(series, day)
        if v is None:
            return None
        pv, _ = asof(series, (dt.date.fromisoformat(d) - dt.timedelta(days=back)).isoformat())
        return pct(v, pv)

    rows = []
    for day in days:
        cal = [k for k, ds in CALENDAR.items() if day in ds]
        nl, nl_d = asof(netliq, day)
        nl_prev, _ = asof(netliq, (dt.date.fromisoformat(nl_d) - dt.timedelta(days=7)).isoformat()) if nl_d else (None, None)
        r10, r10_d = asof(real10, day)
        r10_prev, _ = asof(real10, (dt.date.fromisoformat(r10_d) - dt.timedelta(days=7)).isoformat()) if r10_d else (None, None)
        dx, dx_d = asof(dxy, day)
        st, st_d = asof(stables, day)
        s, s_d = asof(spx, day)
        n, n_d = asof(ndx, day)
        vx, vx_d = asof(vix, day)
        h, h_d = asof(hy, day)
        h_prev, _ = asof(hy, (dt.date.fromisoformat(h_d) - dt.timedelta(days=7)).isoformat()) if h_d else (None, None)

        pos = {}
        for c in ("btc", "eth"):
            r = dict(okx[c].get(day, {}))
            prev = okx[c].get((dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat(), {})
            if r.get("oi_usd") and prev.get("oi_usd"):
                r["oi_chg_pct"] = pct(r["oi_usd"], prev["oi_usd"])
            for x in (r, prev):
                if not x.get("oi_coin") and x.get("oi_usd") and x.get("close"):
                    x["oi_coin"] = x["oi_usd"] / x["close"]
            if r.get("oi_coin") and prev.get("oi_coin"):
                r["oi_coin_chg_pct"] = pct(r["oi_coin"], prev["oi_coin"])
            if prev.get("close") and r.get("close"):
                r["chg_pct"] = pct(r["close"], prev["close"])
            r["flow"] = flow_label(r.get("chg_pct"), r.get("oi_coin_chg_pct"))
            tb, ts = r.get("taker_buy_usd"), r.get("taker_sell_usd")
            if tb is not None and ts:
                r["taker_buy_share"] = tb / (tb + ts)
            pos[c] = r
        for c, src in (("cot_btc", cot_btc), ("cot_eth", cot_eth)):
            v, d = asof(src, day)
            pos[c] = dict(v, asof=d) if v else None

        corrs = {}
        for k, other in (("btc_spx", spx), ("btc_ndx", ndx), ("btc_dxy", dxy), ("btc_eth", eth_close)):
            cval, npairs = window_corr(btc_close, other, day)
            corrs[k] = cval
            corrs[k + "_n"] = npairs
            c7, n7 = window_corr(btc_close, other, day, days=7, min_n=4)
            corrs[k + "_7d"] = c7
        for k, a in (("btc_gold", btc_close), ("eth_gold", eth_close)):
            corrs[k], corrs[k + "_n"] = window_corr(a, gold, day)
            corrs[k + "_7d"], _ = window_corr(a, gold, day, days=7, min_n=4)

        gd, gd_d = asof(gold, day)
        g_hist = {d: v for d, v in gold.items() if d <= day and d >= (dt.date.fromisoformat(day) - dt.timedelta(days=120)).isoformat()}
        g_hi_d = max(g_hist, key=g_hist.get) if g_hist else None
        cg, cg_d = asof(cotg, day)
        cg_prev, _ = asof(cotg, (dt.date.fromisoformat(cg_d) - dt.timedelta(days=7)).isoformat()) if cg_d else (None, None)
        gt, gt_d = asof(gld, day)
        gt_prev, _ = asof(gld, (dt.date.fromisoformat(gt_d) - dt.timedelta(days=7)).isoformat()) if gt_d else (None, None)
        w, w_d = asof(wti, day)
        b, b_d = asof(brent, day)
        macro = {
            "gold": gd, "gold_asof": gd_d, "gold_src": gold_src, "gold_1d_pct": change(gold, day, 1),
            "gold_7d_pct": change(gold, day, 7),
            "gold_high120": g_hist.get(g_hi_d) if g_hi_d else None, "gold_high120_date": g_hi_d,
            "gold_from_high_pct": pct(gd, g_hist[g_hi_d]) if g_hi_d and gd else None,
            "cot_gold_mm_net": cg["mm_net"] if cg else None, "cot_gold_mm_long": cg["mm_long"] if cg else None,
            "cot_gold_mm_short": cg["mm_short"] if cg else None, "cot_gold_asof": cg_d,
            "cot_gold_mm_net_wk_chg": cg["mm_net"] - cg_prev["mm_net"] if cg and cg_prev else None,
            "gld_tonnes": gt, "gld_asof": gt_d, "gld_7d_chg_t": gt - gt_prev if gt is not None and gt_prev is not None else None,
            "wti": w, "wti_asof": w_d, "wti_1d_pct": change(wti, day, 1),
            "brent": b, "brent_asof": b_d, "brent_1d_pct": change(brent, day, 1),
        }

        rows.append({
            "date": day,
            "cal": cal,
            "regime": {
                "netliq_musd": nl, "netliq_asof": nl_d, "netliq_wk_chg_pct": pct(nl, nl_prev),
                "real10y": r10, "real10y_asof": r10_d, "real10y_wk_chg_bp": (r10 - r10_prev) * 100 if r10 is not None and r10_prev is not None else None,
                "dxy": dx, "dxy_asof": dx_d, "dxy_src": dxy_src, "dxy_7d_pct": change(dxy, day, 7),
                "stables_usd": st, "stables_asof": st_d, "stables_7d_pct": change(stables, day, 7),
                "trend_btc": trend(btc_close, day),
                "trend_eth": trend(eth_close, day),
            },
            "risk": {
                "spx": s, "spx_asof": s_d, "spx_1d_pct": change(spx, day, 1),
                "ndx": n, "ndx_asof": n_d, "ndx_1d_pct": change(ndx, day, 1),
                "vix": vx, "vix_asof": vx_d,
                "hy_oas": h, "hy_asof": h_d, "hy_wk_chg_bp": (h - h_prev) * 100 if h is not None and h_prev is not None else None,
            },
            "pos": pos,
            "macro": macro,
            "corr": corrs,
        })

    os.makedirs(OUT, exist_ok=True)

    def clean(o):
        if isinstance(o, float):
            return None if math.isnan(o) else round(o, 6)
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [clean(v) for v in o]
        return o

    rows = clean(rows)
    weekly = clean({
        "netliq_musd": sorted(netliq.items()),
        "cot_btc_lev_net": sorted((d, v["lev_net"]) for d, v in cot_btc.items()),
        "cot_eth_lev_net": sorted((d, v["lev_net"]) for d, v in cot_eth.items()),
        "cot_gold_mm_net": sorted((d, v["mm_net"]) for d, v in cotg.items()),
    })
    json.dump({"built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "status": status, "calendar": CALENDAR, "weekly": weekly, "rows": rows}, open(f"{OUT}/notebook_daily.json", "w"), indent=1)

    def flat(prefix, o, out):
        for k, v in o.items():
            key = f"{prefix}_{k}" if prefix else k
            if isinstance(v, dict):
                flat(key, v, out)
            elif isinstance(v, list):
                out[key] = "+".join(v)
            else:
                out[key] = "" if v is None else v
        return out

    flats = [flat("", r, {}) for r in rows]
    header = []
    for f in flats:
        for k in f:
            if k not in header:
                header.append(k)
    with open(f"{OUT}/notebook_daily.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, restval="")
        w.writeheader()
        w.writerows(flats)

    for k, v in status.items():
        print(f"{k:22} {v}")
    print("rows", len(rows), rows[0]["date"], "..", rows[-1]["date"], "| columns", len(header))


if __name__ == "__main__":
    main()
