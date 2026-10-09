"""Daily BTC funding (2016→) and coin-denominated OI (2021-12→) for backtests.
Funding: BitMEX XBTUSD until Binance USDT-M starts (2019-09), Binance after; the
day's 8h payments summed, each payment assigned to the day it closes.
OI: Binance BTCUSDT daily metrics archive, value at the end of the UTC day."""
import csv, datetime as dt, io, json, os, time, urllib.parse, urllib.request, zipfile

OUT = "data/research"
UA = {"User-Agent": "Mozilla/5.0 (research; github actions)"}


def fetch(url, kind="json", tries=3):
    err = None
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                b = r.read()
            return json.loads(b) if kind == "json" else b
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"
            if "404" in err:
                break
            time.sleep(2 * (a + 1))
    raise RuntimeError(err)


def day_of(ts):  # settlement closes the prior period
    return (ts - dt.timedelta(milliseconds=1)).strftime("%Y-%m-%d")


def bitmex(start, end):
    out, t = {}, start
    while t < end:
        q = urllib.parse.urlencode({"symbol": "XBTUSD", "startTime": t.isoformat(), "count": 500, "reverse": "false"})
        rows = fetch("https://www.bitmex.com/api/v1/funding?" + q)
        if not rows:
            break
        for r in rows:
            ts = dt.datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
            if ts >= end:
                break
            out[day_of(ts)] = out.get(day_of(ts), 0) + float(r["fundingRate"]) * 100
        t = dt.datetime.fromisoformat(rows[-1]["timestamp"].replace("Z", "+00:00")) + dt.timedelta(seconds=1)
        time.sleep(1.2)  # public rate limit
    return out


def binance_funding(y0, m0):
    out, y, m = {}, y0, m0
    today = dt.date.today()
    while (y, m) <= (today.year, today.month):
        url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{y}-{m:02d}.zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(fetch(url, "bytes")))
            for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))):
                if row and row[0].isdigit():
                    ts = dt.datetime.fromtimestamp(int(row[0]) / 1000, dt.timezone.utc)
                    out[day_of(ts)] = out.get(day_of(ts), 0) + float(row[2]) * 100
        except Exception as e:
            print("binance funding", y, m, e)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def binance_oi(start):
    out, d = {}, start
    while d < dt.date.today():
        url = f"https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{d.isoformat()}.zip"
        try:
            z = zipfile.ZipFile(io.BytesIO(fetch(url, "bytes", tries=2)))
            rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]))))
            if rows:
                out[d.isoformat()] = (float(rows[-1]["sum_open_interest"]), float(rows[-1]["sum_open_interest_value"]))
        except Exception:
            pass
        d += dt.timedelta(days=1)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    utc = dt.timezone.utc
    bm = bitmex(dt.datetime(2016, 1, 1, tzinfo=utc), dt.datetime(2019, 10, 1, tzinfo=utc))
    bn = binance_funding(2019, 9)
    fund = {**bm, **{k: v for k, v in bn.items() if k >= "2019-10-01"}}
    with open(f"{OUT}/btc_funding_daily.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["date", "funding_day_pct", "source"])
        for k in sorted(fund):
            w.writerow([k, round(fund[k], 6), "BitMEX" if k < "2019-10-01" else "Binance"])
    oi = binance_oi(dt.date(2021, 12, 1))
    with open(f"{OUT}/btc_oi_daily.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["date", "oi_coin", "oi_usd"])
        for k in sorted(oi):
            w.writerow([k, round(oi[k][0], 3), round(oi[k][1], 2)])
    print("funding days", len(fund), min(fund), max(fund), "| bitmex", len(bm), "binance", len(bn))
    print("oi days", len(oi), min(oi) if oi else None, max(oi) if oi else None)


if __name__ == "__main__":
    main()
