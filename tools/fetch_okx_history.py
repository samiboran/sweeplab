"""Last N days of daily BTC/ETH derivatives history from OKX public APIs.

Per UTC day and coin: price OHLC, open interest (USD, end of day), long/short
account ratio, taker buy/sell volume (USD) and funding (sum of the day's 8h
payments). Output: data/derivs/okx_history_30d.csv, one row per date, BTC and
ETH side by side. Raw responses are kept in data/derivs/okx_history_raw.json.

Runs on GitHub Actions (OKX is reachable from there; Binance/Bybit block US IPs).
"""
import csv, datetime as dt, json, os, time, urllib.request

DAYS = int(os.environ.get("DAYS", "30"))
COINS = ["BTC", "ETH"]
BASE = "https://www.okx.com"
OUT_DIR = "data/derivs"


def get(path):
    url = BASE + path
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.loads(r.read())
            if str(j.get("code")) == "0":
                return {"ok": True, "url": url, "data": j["data"]}
            err = f"okx code {j.get('code')}: {j.get('msg')}"
        except Exception as e:  # network / HTTP error
            err = str(e)[:300]
        time.sleep(1.5 * (attempt + 1))
    return {"ok": False, "url": url, "error": err}


def utc_day(ms):
    return dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


def fetch(coin):
    inst = f"{coin}-USDT-SWAP"
    return {
        # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]; 1Dutc = UTC-midnight candles
        "candles": get(f"/api/v5/market/history-candles?instId={inst}&bar=1Dutc&limit=100"),
        # [ts, oi(contracts), oiCcy, oiUsd]
        "oi": get(f"/api/v5/rubik/stat/contracts/open-interest-history?instId={inst}&period=1Dutc&limit=100"),
        # [ts, ratio] — share of accounts net long vs net short on this contract
        "ls": get(f"/api/v5/rubik/stat/contracts/long-short-account-ratio-contract?instId={inst}&period=1Dutc&limit=100"),
        # [ts, sellVol, buyVol]; unit=2 -> USD(T)
        "taker": get(f"/api/v5/rubik/stat/taker-volume-contract?instId={inst}&period=1Dutc&unit=2&limit=100"),
        # 8-hourly funding; 100 entries ≈ 33 days
        "funding": get(f"/api/v5/public/funding-rate-history?instId={inst}&limit=100"),
        # coin-level fallbacks (all OKX contracts of that coin)
        "oi_ccy": get(f"/api/v5/rubik/stat/contracts/open-interest-volume?ccy={coin}&period=1D"),
        "ls_ccy": get(f"/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy={coin}&period=1D"),
        "taker_ccy": get(f"/api/v5/rubik/stat/taker-volume?ccy={coin}&instType=CONTRACTS&period=1D"),
    }


def build(raw, coin):
    r = raw[coin]
    rows = {}

    def row(day):
        return rows.setdefault(day, {})

    if r["candles"]["ok"]:
        for c in r["candles"]["data"]:
            if len(c) > 8 and c[8] != "1":
                continue  # skip today's unfinished candle
            d = row(utc_day(c[0]))
            d.update(open=float(c[1]), high=float(c[2]), low=float(c[3]), close=float(c[4]))

    # open interest: prefer per-contract USD OI, fall back to coin-level
    if r["oi"]["ok"] and r["oi"]["data"]:
        for x in r["oi"]["data"]:
            row(utc_day(x[0]))["oi_usd"] = float(x[3])
        rows_src_oi = "BTC/ETH-USDT perp"
    elif r["oi_ccy"]["ok"]:
        for x in r["oi_ccy"]["data"]:
            row(utc_day(x[0]))["oi_usd"] = float(x[1])
        rows_src_oi = "all OKX contracts"
    else:
        rows_src_oi = "missing"

    src = r["ls"] if (r["ls"]["ok"] and r["ls"]["data"]) else r["ls_ccy"]
    if src["ok"]:
        for x in src["data"]:
            row(utc_day(x[0]))["ls_ratio"] = float(x[1])

    src = r["taker"] if (r["taker"]["ok"] and r["taker"]["data"]) else r["taker_ccy"]
    if src["ok"]:
        for x in src["data"]:
            d = row(utc_day(x[0]))
            d["taker_sell_usd"], d["taker_buy_usd"] = float(x[1]), float(x[2])

    if r["funding"]["ok"]:
        for f in r["funding"]["data"]:
            d = row(utc_day(f["fundingTime"]))
            d["funding_sum_pct"] = d.get("funding_sum_pct", 0.0) + float(f["fundingRate"]) * 100
            d["funding_n"] = d.get("funding_n", 0) + 1
    return rows, rows_src_oi


def main():
    raw = {c: fetch(c) for c in COINS}
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump(raw, open(f"{OUT_DIR}/okx_history_raw.json", "w"), indent=1)

    built = {c: build(raw, c) for c in COINS}
    today = dt.datetime.now(dt.timezone.utc).date()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(DAYS, 0, -1)]  # last N full UTC days

    fields = ["open", "high", "low", "close", "oi_usd", "oi_chg_pct", "ls_ratio",
              "taker_buy_usd", "taker_sell_usd", "taker_buy_share", "funding_sum_pct", "funding_n"]
    header = ["date"] + [f"{c.lower()}_{f}" for c in COINS for f in fields]
    out_rows = []
    for day in days:
        line = {"date": day}
        for c in COINS:
            rows = built[c][0]
            d = dict(rows.get(day, {}))
            prev = rows.get((dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat(), {})
            if d.get("oi_usd") and prev.get("oi_usd"):
                d["oi_chg_pct"] = (d["oi_usd"] / prev["oi_usd"] - 1) * 100
            if d.get("taker_buy_usd") is not None and d.get("taker_sell_usd") is not None:
                tot = d["taker_buy_usd"] + d["taker_sell_usd"]
                if tot:
                    d["taker_buy_share"] = d["taker_buy_usd"] / tot
            for f in fields:
                v = d.get(f)
                if isinstance(v, float):
                    v = round(v, 6 if f in ("funding_sum_pct", "taker_buy_share", "ls_ratio") else 2)
                line[f"{c.lower()}_{f}"] = "" if v is None else v
        out_rows.append(line)

    with open(f"{OUT_DIR}/okx_history_30d.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(out_rows)

    # status report for the workflow log
    for c in COINS:
        for k, v in raw[c].items():
            n = len(v["data"]) if v["ok"] else 0
            span = ""
            if v["ok"] and v["data"]:
                ts = [int(x["fundingTime"] if isinstance(x, dict) else x[0]) for x in v["data"]]
                span = f"{utc_day(min(ts))}..{utc_day(max(ts))}"
            print(f"{c:3} {k:10} {'OK ' + str(n) + ' ' + span if v['ok'] else 'ERR ' + v['error']}")
        print(f"{c} OI source: {built[c][1]}")
    filled = {f: sum(1 for r in out_rows if r[f] != "") for f in header[1:]}
    print("filled cells per column (of", len(out_rows), "):", filled)


if __name__ == "__main__":
    main()
