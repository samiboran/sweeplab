"""Estimated liquidation map for BTC / ETH from OKX open-interest history.

Idea: every rise in open interest is new contracts, i.e. a new long AND a new short
opened at that moment's price. We don't know their leverage, so each new cohort is
spread over four tiers (10x / 25x / 50x / 100x). Falls in open interest close existing
cohorts proportionally. A tier of a cohort counts as liquidated once a later 4h candle
traded through its liquidation price. What is left, binned by price, is where forced
selling (long liquidations, below price) and forced buying (short liquidations, above
price) would still be triggered.

This is a model, not exchange data: real leverage, margin mode and stops are unknown.
Unlike volume-based TradingView indicators, it is built only from contracts that were
actually opened (OKX BTC/ETH-USDT perp, ~5-6% of the market).

Output: OUT_DIR/liq_map.json (latest) and OUT_DIR/liq_maps/<date>.json (history,
used later to check which bands were swept).
"""
import datetime as dt, json, os, time, urllib.request

OUT = os.environ.get("OUT_DIR", "data/derivs")
BASE = "https://www.okx.com"
COINS = ["BTC", "ETH", "SOL"]
DAYS = int(os.environ.get("LIQ_DAYS", "45"))
TIERS = {10: 0.35, 25: 0.30, 50: 0.20, 100: 0.15}   # assumed share of new positions per leverage
MM = 0.005                                          # maintenance margin, moves liquidation 0.5% closer
BIN_PCT = 0.25                                      # price bins as % of current price
RANGE_PCT = 12.0                                    # keep bins within ±12% of price


def get(path):
    for attempt in range(3):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.loads(r.read())
            if str(j.get("code")) == "0":
                return j["data"]
            err = f"okx {j.get('code')}: {j.get('msg')}"
        except Exception as e:
            err = str(e)[:200]
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{path}: {err}")


def paged(path_fmt, key_ts, since_ms, max_pages=12):
    """Page backwards (newest first) until `since_ms` is covered."""
    rows, end = [], None
    for _ in range(max_pages):
        data = get(path_fmt(end))
        if not data:
            break
        rows += data
        oldest = min(int(key_ts(x)) for x in data)
        if oldest <= since_ms:
            break
        end = oldest
    out = {int(key_ts(x)): x for x in rows if int(key_ts(x)) >= since_ms}
    return [out[k] for k in sorted(out)]


def fetch(coin, since_ms):
    inst = f"{coin}-USDT-SWAP"
    oi = paged(lambda end: f"/api/v5/rubik/stat/contracts/open-interest-history?instId={inst}&period=4H&limit=100"
               + (f"&end={end - 1}" if end else ""), lambda x: x[0], since_ms)
    candles = paged(lambda end: f"/api/v5/market/history-candles?instId={inst}&bar=4H&limit=100"
                    + (f"&after={end}" if end else ""), lambda x: x[0], since_ms)
    return oi, candles


def build_map(oi, candles):
    """oi rows [ts, oi, oiCcy, oiUsd]; candles [ts, o, h, l, c, ...] (4h, ts = bar open)."""
    bars = {int(c[0]): (float(c[2]), float(c[3]), float(c[4])) for c in candles}
    bar_ts = sorted(bars)
    cohorts = []   # dicts: price, amt (coins), alive {(side, lev): True}
    prev_oi = None
    for row in oi:
        ts, oi_ccy, oi_usd = int(row[0]), float(row[2]), float(row[3])
        price = oi_usd / oi_ccy if oi_ccy else None
        if prev_oi is not None and price:
            d = oi_ccy - prev_oi
            if d > 0:
                cohorts.append({"ts": ts, "price": price, "amt": d,
                                "alive": {(s, L): True for s in ("long", "short") for L in TIERS}})
            elif d < 0:
                tot = sum(c["amt"] for c in cohorts)
                if tot > 0:
                    k = max(0.0, 1 + d / tot)
                    for c in cohorts:
                        c["amt"] *= k
        prev_oi = oi_ccy
    # liquidation check: any 4h bar after the cohort opened that traded through its level
    for c in cohorts:
        later = [bars[t] for t in bar_ts if t >= c["ts"]]
        lo = min((b[1] for b in later), default=None)
        hi = max((b[0] for b in later), default=None)
        for L in TIERS:
            liq_long = c["price"] * (1 - 1 / L + MM)
            liq_short = c["price"] * (1 + 1 / L - MM)
            if lo is not None and lo <= liq_long:
                c["alive"][("long", L)] = False
            if hi is not None and hi >= liq_short:
                c["alive"][("short", L)] = False
    last_close = bars[bar_ts[-1]][2] if bar_ts else None
    return cohorts, last_close


def bin_map(cohorts, price):
    step = price * BIN_PCT / 100
    bins = {}
    for c in cohorts:
        for (side, L), alive in c["alive"].items():
            if not alive or c["amt"] <= 0:
                continue
            lvl = c["price"] * ((1 - 1 / L + MM) if side == "long" else (1 + 1 / L - MM))
            if abs(lvl / price - 1) * 100 > RANGE_PCT:
                continue
            b = round(lvl / step) * step
            e = bins.setdefault(round(b, 2), {"long": 0.0, "short": 0.0, "tiers": {}})
            amt = c["amt"] * TIERS[L]
            e[side] += amt
            e["tiers"][L] = e["tiers"].get(L, 0.0) + amt
    rows = []
    for b, e in sorted(bins.items()):
        top = max(e["tiers"], key=e["tiers"].get)
        rows.append({"price": b, "long": round(e["long"], 3), "short": round(e["short"], 3), "lev": top})
    return rows


def clusters(rows, price, side, n=3):
    """Strongest bands on one side: local peaks of a 3-bin rolling sum."""
    step = price * BIN_PCT / 100
    pts = sorted((r for r in rows if r[side] > 0 and ((r["price"] < price) if side == "long" else (r["price"] > price))),
                 key=lambda r: r["price"])
    if not pts:
        return []
    by = {round(r["price"] / step): r for r in pts}
    keys = sorted(by)
    sm = {k: sum(by[j][side] for j in (k - 1, k, k + 1) if j in by) for k in keys}
    peaks = [k for k in keys if sm[k] > 0 and sm[k] >= sm.get(k - 1, 0) and sm[k] > sm.get(k + 1, 0)]
    total = sum(r[side] for r in pts) or 1
    out = []
    for k in sorted(peaks, key=lambda k: -sm[k])[:n]:
        lev_amt = {}
        for j in (k - 1, k, k + 1):
            if j in by:
                lev_amt[by[j]["lev"]] = lev_amt.get(by[j]["lev"], 0) + by[j][side]
        pr = by[k]["price"]
        out.append({"price": pr, "from": round((k - 1) * step, 2), "to": round((k + 1) * step, 2),
                    "amt": round(sm[k], 3), "usd": round(sm[k] * price), "share_pct": round(sm[k] / total * 100, 1),
                    "dist_pct": round((pr / price - 1) * 100, 2), "lev": max(lev_amt, key=lev_amt.get)})
    return sorted(out, key=lambda x: abs(x["dist_pct"]))


def main():
    now = dt.datetime.now(dt.timezone.utc)
    since = int((now - dt.timedelta(days=DAYS)).timestamp() * 1000)
    result = {"built_utc": now.isoformat(timespec="seconds"), "days": DAYS, "tiers": TIERS,
              "bin_pct": BIN_PCT, "source": "OKX USDT perp OI (4h) + 4h candles", "coins": {}}
    for coin in COINS:
        try:
            oi, candles = fetch(coin, since)
            cohorts, last = build_map(oi, candles)
            price = last
            rows = bin_map(cohorts, price)
            result["coins"][coin.lower()] = {
                "price": price, "oi_points": len(oi), "candles": len(candles),
                "first": dt.datetime.fromtimestamp(int(oi[0][0]) / 1000, dt.timezone.utc).isoformat() if oi else None,
                "long_bands": clusters(rows, price, "long"), "short_bands": clusters(rows, price, "short"),
                "bins": rows}
            print(coin, "oi", len(oi), "candles", len(candles), "bins", len(rows))
            for side in ("long_bands", "short_bands"):
                print(" ", side, [(round(b["price"]), b["lev"], b["share_pct"]) for b in result["coins"][coin.lower()][side]])
        except Exception as e:
            result["coins"][coin.lower()] = {"error": str(e)[:300]}
            print(coin, "ERROR", e)
    os.makedirs(f"{OUT}/liq_maps", exist_ok=True)
    json.dump(result, open(f"{OUT}/liq_map.json", "w"), indent=1)
    json.dump(result, open(f"{OUT}/liq_maps/{now.date().isoformat()}.json", "w"))


if __name__ == "__main__":
    main()
