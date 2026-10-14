"""4h screener for large caps on OKX USDT perps: who sits on support and looks ready
to break up, and who sits under resistance / is breaking down.

Per coin (last 200 4h candles): EMA20/50/200, 30-bar (5-day) range high/low and
where price sits in it, Bollinger width percentile (squeeze), 7-day strength vs BTC,
24h coin-OI change and funding. Printed as a table; nothing here is a signal.
"""
import json, time, urllib.request

BASE = "https://www.okx.com"
COINS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX", "LINK", "SUI", "TRX", "DOT", "TON",
         "LTC", "BCH", "HYPE", "NEAR", "APT", "UNI", "AAVE", "PEPE", "ARB", "OP", "ENA", "WLD"]


def get(path):
    for a in range(3):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                j = json.loads(r.read())
            if str(j.get("code")) == "0":
                return j["data"]
            return []
        except Exception:
            time.sleep(1 + a)
    return []


def ema(v, n):
    k, e = 2 / (n + 1), v[0]
    for x in v[1:]:
        e = x * k + e * (1 - k)
    return e


def candles(inst):
    a = get(f"/api/v5/market/candles?instId={inst}&bar=4H&limit=300")
    a = sorted(a, key=lambda x: int(x[0]))
    a = [x for x in a if len(x) < 9 or x[8] == "1"] + ([a[-1]] if a and len(a[-1]) > 8 and a[-1][8] != "1" else [])
    return [(int(x[0]), float(x[2]), float(x[3]), float(x[4])) for x in a]


rows, btc7 = [], None
for coin in COINS:
    inst = f"{coin}-USDT-SWAP"
    c = candles(inst)
    if len(c) < 60:
        continue
    cl = [x[3] for x in c]
    px = cl[-1]
    e20, e50 = ema(cl[-120:], 20), ema(cl[-200:], 50)
    e200 = ema(cl, 200) if len(cl) >= 200 else None
    hi30 = max(x[1] for x in c[-31:-1]); lo30 = min(x[2] for x in c[-31:-1])
    pos = (px - lo30) / (hi30 - lo30) * 100 if hi30 > lo30 else 50
    widths = []
    for i in range(20, len(cl) + 1):
        w = cl[i - 20:i]; m = sum(w) / 20; sd = (sum((x - m) ** 2 for x in w) / 20) ** 0.5
        widths.append(4 * sd / m)
    bbp = sum(1 for w in widths[-120:] if w <= widths[-1]) / len(widths[-120:]) * 100
    ch7 = (px / cl[-43] - 1) * 100 if len(cl) > 43 else None
    if coin == "BTC":
        btc7 = ch7
    oi = get(f"/api/v5/rubik/stat/contracts/open-interest-history?instId={inst}&period=4H&limit=7")
    oi = sorted(oi, key=lambda x: int(x[0]))
    oi24 = (float(oi[-1][2]) / float(oi[0][2]) - 1) * 100 if len(oi) >= 7 and float(oi[0][2]) else None
    fr = get(f"/api/v5/public/funding-rate?instId={inst}")
    f = float(fr[0]["fundingRate"]) * 100 if fr else None
    trend = sum([px > e20, e20 > e50, (e200 is not None and e50 > e200), (e200 is not None and px > e200)])
    hi6 = max(x[1] for x in c[-6:])
    res = min([v for v in (e50, e200, hi30) if v is not None and v >= px], default=None)
    rej = res is not None and hi6 >= res * 0.99 and px < res
    rows.append(dict(coin=coin, px=px, trend=trend, hi6=hi6, rej=rej, res=res, off_hi6=(px / hi6 - 1) * 100, e50=e50, e200=e200, hi=hi30, lo=lo30, pos=pos, bbp=bbp,
                     ch7=ch7, oi24=oi24, f=f, d_hi=(hi30 / px - 1) * 100, d_lo=(px / lo30 - 1) * 100))
    time.sleep(0.15)

for r in rows:
    r["rs"] = (r["ch7"] - btc7) if r["ch7"] is not None and btc7 is not None else None
    up = r["trend"] * 1.0 + (1 if r["rs"] and r["rs"] > 0 else 0) + (1 if r["d_hi"] < 2 else 0) + (0.5 if r["bbp"] < 25 else 0)
    dn = (4 - r["trend"]) * 1.0 + (1 if r["rs"] and r["rs"] < 0 else 0) + (1 if r["d_lo"] < 2 else 0) + (0.5 if r["bbp"] < 25 else 0)
    r["score"] = up - dn

print("DİRENÇTEN DÖNENLER (son 24s tepe EMA50/EMA200/5g tepeye değdi, fiyat altında):")
for r in sorted([r for r in rows if r["rej"] and r["trend"] <= 2], key=lambda r: r["off_hi6"]):
    print(f"  {r['coin']:5} fiyat {r['px']:.6g} · 24s tepe {r['hi6']:.6g} ({r['off_hi6']:+.1f}%) · direnç {r['res']:.6g} · trend {r['trend']}/4 · OI24s {r['oi24'] if r['oi24'] is not None else float('nan'):+.1f}% · funding {r['f'] if r['f'] is not None else float('nan'):+.4f} · 5g dip {r['lo']:.6g}")
print()
print("coin   fiyat        trend  aralık%  tepeye%  dibe%  sıkışma%  7g   BTC'ye göre  OI24s%  funding%  skor")
for r in sorted(rows, key=lambda r: -r["score"]):
    p = r["px"]; fmt = (lambda v: f"{v:.6f}") if p < 0.01 else (lambda v: f"{v:.4f}") if p < 10 else (lambda v: f"{v:.2f}")
    print(f"{r['coin']:5} {fmt(p):>11}  {r['trend']}/4  {r['pos']:6.0f}  {r['d_hi']:6.1f}  {r['d_lo']:5.1f}  {r['bbp']:7.0f}  "
          f"{(r['ch7'] or 0):+5.1f}  {(r['rs'] or 0):+6.1f}  {(r['oi24'] if r['oi24'] is not None else float('nan')):+6.1f}  "
          f"{(r['f'] if r['f'] is not None else float('nan')):+.4f}  {r['score']:+.1f}  | 5g aralık {fmt(r['lo'])}–{fmt(r['hi'])}"
          f" · EMA50 {fmt(r['e50'])}" + (f" · EMA200 {fmt(r['e200'])}" if r['e200'] else ""))
