"""Daily data around the start of each BTC bull regime (30 days before → 60 days after).

Bull start = first day of a run of >= 60 days where close > MA200 and MA50 > MA200
(same rule as the notebook), computed from Bitstamp daily closes. One CSV row per
(window, date). Nothing is interpreted here; it is a reference dataset.

Sources (all public, no keys): Yahoo (BTC-USD, ETH-USD, DX-Y.NYB, GC=F, ^GSPC, ^IXIC,
^VIX), FRED (HY spread, 10y real yield, WALCL, WTREGEN, RRPONTSYD, WTI), DefiLlama
(stablecoin supply), Binance public archive (funding; OI and L/S from 2021-12),
BitMEX (funding before Binance futures existed), CFTC (CME BTC leveraged funds,
COMEX gold managed money).
"""
import csv, datetime as dt, io, json, os, time, urllib.parse, urllib.request, zipfile

OUT = "data/cycles"
UA = {"User-Agent": "Mozilla/5.0 (cycle-windows; github actions)"}
BEFORE, AFTER = 30, 60
STARTS = {  # from tools/build_notebook.py's trend rule on Bitstamp closes
    "2019-04 rally": "2019-04-23",
    "2020-05 bull": "2020-05-21",
    "2021-10 leg": "2021-10-01",
    "2023-02 rally": "2023-02-07",
    "2023-10 bull": "2023-10-30",
    "2024-10 leg": "2024-10-28",
    "2025-05 leg": "2025-05-22",
}
status = {}


def fetch(url, kind="json", tries=3, data=None):
    err = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA, data=data)
            with urllib.request.urlopen(req, timeout=40) as r:
                b = r.read()
            return json.loads(b) if kind == "json" else (b if kind == "bytes" else b.decode("utf-8", "replace"))
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:150]}"
            if "404" in err:
                break
            time.sleep(2 * (a + 1))
    raise RuntimeError(err)


def d2s(x):
    return x.strftime("%Y-%m-%d")


def yahoo(sym, start, end):
    p1 = int(dt.datetime.combine(start, dt.time(), dt.timezone.utc).timestamp())
    p2 = int(dt.datetime.combine(end + dt.timedelta(days=2), dt.time(), dt.timezone.utc).timestamp())
    try:
        j = fetch(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={p1}&period2={p2}&interval=1d")
        r = j["chart"]["result"][0]
        out = {d2s(dt.datetime.fromtimestamp(t, dt.timezone.utc)): float(c)
               for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None}
        status.setdefault("yahoo:" + sym, []).append(len(out))
        return out
    except Exception as e:
        status.setdefault("yahoo:" + sym, []).append("ERR " + str(e))
        return {}


def fred(series, start, end):
    try:
        txt = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={d2s(start)}&coed={d2s(end)}", "text")
        out = {r[0]: float(r[1]) for r in csv.reader(io.StringIO(txt)) if len(r) == 2 and r[0][:2] in ("19", "20") and r[1] not in (".", "")}
        status.setdefault(series, []).append(len(out))
        return out
    except Exception as e:
        status.setdefault(series, []).append("ERR " + str(e))
        return {}


_stables = None


def stables():
    global _stables
    if _stables is None:
        try:
            j = fetch("https://stablecoins.llama.fi/stablecoincharts/all")
            _stables = {d2s(dt.datetime.fromtimestamp(int(x["date"]), dt.timezone.utc)): float((x.get("totalCirculatingUSD") or {}).get("peggedUSD") or 0) for x in j}
            status["stablecoins"] = [len(_stables)]
        except Exception as e:
            _stables = {}
            status["stablecoins"] = ["ERR " + str(e)]
    return _stables


def binance_funding(sym, start, end):
    """Monthly funding archive -> {date: sum of the day's funding in %}."""
    out, months = {}, sorted({(d.year, d.month) for d in (start + dt.timedelta(days=i) for i in range((end - start).days + 1))})
    for y, m in months:
        url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{y}-{m:02d}.zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(fetch(url, "bytes")))
            for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))):
                if not row or not row[0].isdigit():
                    continue
                t = dt.datetime.fromtimestamp(int(row[0]) / 1000 - 0.001, dt.timezone.utc)  # settlement closes the prior period
                out[d2s(t)] = out.get(d2s(t), 0) + float(row[2]) * 100
        except Exception as e:
            status.setdefault("binance_funding:" + sym, []).append(f"{y}-{m:02d} ERR {e}")
    status.setdefault("binance_funding:" + sym, []).append(len(out))
    return out


def bitmex_funding(start, end):
    q = urllib.parse.urlencode({"symbol": "XBTUSD", "startTime": d2s(start), "endTime": d2s(end + dt.timedelta(days=1)), "count": 500})
    try:
        rows = fetch("https://www.bitmex.com/api/v1/funding?" + q)
        out = {}
        for r in rows:
            t = dt.datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) - dt.timedelta(milliseconds=1)
            out[d2s(t)] = out.get(d2s(t), 0) + float(r["fundingRate"]) * 100
        status.setdefault("bitmex_funding", []).append(len(out))
        return out
    except Exception as e:
        status.setdefault("bitmex_funding", []).append("ERR " + str(e))
        return {}


def bitmex_oi(start, end):
    """BitMEX XBTUSD daily open interest (USD contracts) — the only free OI history
    before Binance's archive starts in Dec 2021. One exchange, so read direction only."""
    q = urllib.parse.urlencode({"symbol": "XBTUSD", "binSize": "1d", "startTime": d2s(start), "endTime": d2s(end + dt.timedelta(days=1)), "count": 500})
    try:
        rows = fetch("https://www.bitmex.com/api/v1/trade/bucketed?" + q)
        out = {}
        for r in rows:
            if r.get("openInterest") is None:
                continue
            t = dt.datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) - dt.timedelta(milliseconds=1)
            out[d2s(t)] = float(r["openInterest"])
        status.setdefault("bitmex_oi", []).append(len(out))
        return out
    except Exception as e:
        status.setdefault("bitmex_oi", []).append("ERR " + str(e))
        return {}


def binance_metrics(sym, start, end):
    """Daily metrics archive (from 2021-12): OI in coins/USD and L/S ratios, end of day."""
    out = {}
    day = start
    while day <= end:
        url = f"https://data.binance.vision/data/futures/um/daily/metrics/{sym}/{sym}-metrics-{d2s(day)}.zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(fetch(url, "bytes", tries=2)))
            rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]))))
            if rows:
                last = rows[-1]
                f = lambda k: float(last[k]) if last.get(k) not in (None, "") else None
                out[d2s(day)] = {"oi_coin": f("sum_open_interest"), "oi_usd": f("sum_open_interest_value"),
                                 "ls_accounts": f("count_long_short_ratio"),
                                 "ls_top_accounts": f("count_toptrader_long_short_ratio"),
                                 "ls_top_positions": f("sum_toptrader_long_short_ratio")}
        except Exception:
            pass
        day += dt.timedelta(days=1)
    status.setdefault("binance_metrics:" + sym, []).append(len(out))
    return out


def cot(dataset, code, fields, start, end):
    q = urllib.parse.urlencode({"$where": f"cftc_contract_market_code='{code}' AND report_date_as_yyyy_mm_dd between '{d2s(start - dt.timedelta(days=10))}T00:00:00' and '{d2s(end)}T00:00:00'",
                                "$order": "report_date_as_yyyy_mm_dd", "$limit": "100"})
    try:
        rows = fetch(f"https://publicreporting.cftc.gov/resource/{dataset}.json?" + q)
        out = {r["report_date_as_yyyy_mm_dd"][:10]: float(r.get(fields[0]) or 0) - float(r.get(fields[1]) or 0) for r in rows}
        status.setdefault(f"cot:{code}", []).append(len(out))
        return out
    except Exception as e:
        status.setdefault(f"cot:{code}", []).append("ERR " + str(e))
        return {}


def asof(series, day):
    keys = [k for k in series if k <= day]
    if not keys:
        return None, None
    k = max(keys)
    return series[k], k


# Price peaks before a 15%+ drawdown (Bitstamp closes). "tepe" = became a bear market
# (50%+ fall, no new high for months); "duzeltme" = 15-35% pullback inside a bull,
# followed by a new high. Used to ask whether the first month after a top looks
# different from the first month after a mere correction.
PEAKS = {
    "2017-12 tepe": ("2017-12-16", "tepe"),
    "2019-06 tepe": ("2019-06-26", "tepe"),
    "2021-04 tepe": ("2021-04-13", "tepe"),
    "2021-11 tepe": ("2021-11-08", "tepe"),
    "2025-10 tepe": ("2025-10-06", "tepe"),
    "2017-09 duzeltme": ("2017-09-01", "duzeltme"),
    "2021-01 duzeltme": ("2021-01-08", "duzeltme"),
    "2021-02 duzeltme": ("2021-02-21", "duzeltme"),
    "2021-03 duzeltme": ("2021-03-13", "duzeltme"),
    "2024-03 duzeltme": ("2024-03-13", "duzeltme"),
    "2024-12 duzeltme": ("2024-12-17", "duzeltme"),
}


def main():
    build({k: (v, "boga_baslangici") for k, v in STARTS.items()}, BEFORE, AFTER, "bull_start_windows.csv", "bull_start")
    build(PEAKS, 30, 30, "peak_windows.csv", "peak")


def build(events, before, after, outfile, anchor_name):
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for name, (s, kind) in events.items():
        s0 = dt.date.fromisoformat(s)
        a, b = s0 - dt.timedelta(days=before), s0 + dt.timedelta(days=after)
        pad = a - dt.timedelta(days=14)  # for weekly / as-of values at the window's first days
        btc, eth = yahoo("BTC-USD", a, b), yahoo("ETH-USD", a, b)
        dxy, gold, spx, ndx, vix = (yahoo(x, pad, b) for x in ("DX-Y.NYB", "GC=F", "^GSPC", "^IXIC", "^VIX"))
        if not vix:
            vix = fred("VIXCLS", pad, b)
        # FRED only serves the last ~3 years of ICE BofA spreads, so early windows stay empty.
        hy, real10, wti = fred("BAMLH0A0HYM2", pad, b), fred("DFII10", pad, b), fred("DCOILWTICO", pad, b)
        walcl, tga, rrp = fred("WALCL", pad, b), fred("WTREGEN", pad, b), fred("RRPONTSYD", pad, b)
        fund_b = binance_funding("BTCUSDT", a, b) if s0 >= dt.date(2019, 10, 1) else {}
        fund_e = binance_funding("ETHUSDT", a, b) if s0 >= dt.date(2019, 12, 1) else {}
        fund_x = bitmex_funding(a, b) if not fund_b else {}
        btc_oi_x = bitmex_oi(a, b) if s0 < dt.date(2021, 12, 1) else {}
        met_b = binance_metrics("BTCUSDT", a, b) if a >= dt.date(2021, 12, 1) else {}
        met_e = binance_metrics("ETHUSDT", a, b) if a >= dt.date(2021, 12, 1) else {}
        cot_btc = cot("gpe5-46if", "133741", ("lev_money_positions_long", "lev_money_positions_short"), pad, b) if s0 >= dt.date(2018, 1, 1) else {}
        cot_gold = cot("72hh-3qpy", "088691", ("m_money_positions_long_all", "m_money_positions_short_all"), pad, b)
        st = stables()
        for i in range((b - a).days + 1):
            d = a + dt.timedelta(days=i)
            ds = d2s(d)
            netliq = None
            w, wd = asof(walcl, ds)
            if w is not None:
                t, _ = asof(tga, wd)
                r, _ = asof(rrp, wd)
                if t is not None:
                    netliq = (w - t - (r or 0) * 1000) / 1e6  # USD trillions
            mb, me = met_b.get(ds, {}), met_e.get(ds, {})
            rows.append({
                "window": name, "event_type": kind, anchor_name: s, "date": ds, "day_offset": (d - s0).days,
                "phase": "once" if d < s0 else ("olay_gunu" if d == s0 else "sonra"),
                "btc_close": btc.get(ds), "eth_close": eth.get(ds),
                "btc_funding_day_pct": fund_b.get(ds, fund_x.get(ds)),
                "btc_funding_src": "Binance" if ds in fund_b else ("BitMEX" if ds in fund_x else ""),
                "eth_funding_day_pct": fund_e.get(ds),
                "btc_oi_coin": mb.get("oi_coin"), "btc_oi_usd": mb.get("oi_usd"),
                "bitmex_xbt_oi_usd": btc_oi_x.get(ds),
                "btc_ls_accounts": mb.get("ls_accounts"), "btc_ls_top_positions": mb.get("ls_top_positions"),
                "eth_oi_coin": me.get("oi_coin"), "eth_oi_usd": me.get("oi_usd"),
                "eth_ls_accounts": me.get("ls_accounts"), "eth_ls_top_positions": me.get("ls_top_positions"),
                "stablecoins_usd_bn": round(st[ds] / 1e9, 2) if st.get(ds) else None,
                "dxy": asof(dxy, ds)[0], "gold": asof(gold, ds)[0], "spx": asof(spx, ds)[0],
                "nasdaq": asof(ndx, ds)[0], "vix": asof(vix, ds)[0], "hy_spread_pct": asof(hy, ds)[0],
                "real10y_pct": asof(real10, ds)[0], "wti": asof(wti, ds)[0],
                "net_liquidity_usd_tn": round(netliq, 3) if netliq is not None else None,
                "cot_cme_btc_levfunds_net": asof(cot_btc, ds)[0], "cot_gold_mm_net": asof(cot_gold, ds)[0],
                "market_open": ds in spx,
            })
    header = list(rows[0].keys())
    with open(f"{OUT}/{outfile}", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else (round(v, 6) if isinstance(v, float) else v)) for k, v in r.items()})
    json.dump(status, open(f"{OUT}/status_{anchor_name}.json", "w"), indent=1)
    for k, v in status.items():
        print(f"{k:28} {v}")
    print("rows", len(rows))


if __name__ == "__main__":
    main()
