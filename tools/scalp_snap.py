"""On-demand 5-minute snapshot for BTC/ETH (OKX USDT perp), printed to the log.

Last 2 hours of 5m candles, 5m open interest (coins), taker buy/sell,
funding, latest liquidations, order-book imbalance (top 50 levels).
Nothing is stored; run via the scalp-snap workflow and read the log.
"""
import datetime as dt, json, time, urllib.request

BASE = "https://www.okx.com"


def get(path):
    for a in range(3):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                j = json.loads(r.read())
            if str(j.get("code")) == "0":
                return j["data"]
        except Exception:
            pass
        time.sleep(1 + a)
    return []


def t(ms):
    return (dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc) + dt.timedelta(hours=3)).strftime("%H:%M")


for coin in ("BTC", "ETH"):
    inst = f"{coin}-USDT-SWAP"
    c = sorted(get(f"/api/v5/market/candles?instId={inst}&bar=5m&limit=24"), key=lambda x: int(x[0]))
    oi = {int(x[0]): float(x[2]) for x in get(f"/api/v5/rubik/stat/contracts/open-interest-history?instId={inst}&period=5m&limit=24")}
    tk = {int(x[0]): (float(x[1]), float(x[2])) for x in get(f"/api/v5/rubik/stat/taker-volume-contract?instId={inst}&period=5m&unit=2&limit=24")}
    fr = get(f"/api/v5/public/funding-rate?instId={inst}")
    bk = get(f"/api/v5/market/books?instId={inst}&sz=50")
    lq = get(f"/api/v5/public/liquidation-orders?instType=SWAP&instFamily={coin}-USDT&state=filled&limit=100")
    print(f"\n===== {coin} (İstanbul saati) =====")
    print("saat   açılış    yüksek    düşük     kapanış  | OI(coin)  ΔOI%  | taker alış%")
    for x in c:
        ts = int(x[0]); o = oi.get(ts); po = oi.get(ts - 300000)
        d = f"{(o / po - 1) * 100:+.2f}" if o and po else "  –  "
        s, b = tk.get(ts, (0, 0)); share = f"{b / (b + s) * 100:.0f}" if b + s else "–"
        print(f"{t(ts)}  {float(x[1]):>9.2f} {float(x[2]):>9.2f} {float(x[3]):>9.2f} {float(x[4]):>9.2f} | {o or 0:>9.1f} {d:>6} | {share}")
    if fr:
        print(f"funding (8s): %{float(fr[0]['fundingRate']) * 100:.4f}")
    if bk:
        bids = sum(float(x[1]) for x in bk[0]["bids"]); asks = sum(float(x[1]) for x in bk[0]["asks"])
        print(f"emir defteri (ilk 50 kademe): alış {bids:.0f} / satış {asks:.0f} kontrat → alış payı %{bids / (bids + asks) * 100:.0f}"
              f" · en iyi alış {bk[0]['bids'][0][0]} satış {bk[0]['asks'][0][0]}")
    det = []
    for g in lq:
        det += g.get("details", [])
    cutoff = time.time() * 1000 - 2 * 3600 * 1000
    det = [x for x in det if int(x["ts"]) >= cutoff]
    lng = sum(float(x["sz"]) for x in det if x["posSide"] == "long" or x.get("side") == "sell")
    sht = sum(float(x["sz"]) for x in det if x["posSide"] == "short" or x.get("side") == "buy")
    print(f"son 2 saat likidasyon (OKX, kontrat): long {lng:.0f} · short {sht:.0f}")
    for x in sorted(det, key=lambda x: -float(x["sz"]))[:5]:
        print(f"   {t(x['ts'])} {x['posSide']:5} {x['sz']:>8} kontrat @ {x['bkPx']}")
