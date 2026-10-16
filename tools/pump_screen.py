"""Pump screener: which liquid OKX USDT perps went up the most, and are they rolling over?

Universe: every USDT-SWAP with > MIN_VOL_USD 24h volume. Ranked by 7-day and 30-day gain
(daily candles). For the top names: drawdown from the recent peak, daily RSI14, 4h EMA20
position and whether the last 4h highs are falling, funding and 24h OI change.
A short idea needs BOTH a big pump AND signs of rolling over; a pump alone is not a short.
"""
import json, time, urllib.request

BASE = "https://www.okx.com"
MIN_VOL_USD = 5e6
TOP = 18


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


def rsi(cl, n=14):
    g = l = 0.0
    for i in range(1, n + 1):
        d = cl[i] - cl[i - 1]; g += max(d, 0); l += max(-d, 0)
    g /= n; l /= n
    for i in range(n + 1, len(cl)):
        d = cl[i] - cl[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n; l = (l * (n - 1) + max(-d, 0)) / n
    return 100 - 100 / (1 + g / l) if l else 100


def bars(inst, bar, limit):
    a = sorted(get(f"/api/v5/market/candles?instId={inst}&bar={bar}&limit={limit}"), key=lambda x: int(x[0]))
    return [(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in a]


tick = get("/api/v5/market/tickers?instType=SWAP")
uni = []
for t in tick:
    if not t["instId"].endswith("-USDT-SWAP"):
        continue
    last = float(t["last"] or 0); o24 = float(t["sodUtc0"] or 0) or float(t["open24h"] or 0)
    vol = float(t.get("volCcy24h") or 0) * last
    if vol >= MIN_VOL_USD and last > 0:
        uni.append({"inst": t["instId"], "coin": t["instId"].split("-")[0], "last": last, "vol": vol,
                    "ch24": (last / float(t["open24h"]) - 1) * 100 if float(t["open24h"] or 0) else 0})
print(f"universe: {len(uni)} USDT perps with >${MIN_VOL_USD/1e6:.0f}M 24h volume")

for u in uni:
    d = bars(u["inst"], "1D", 60)
    time.sleep(0.07)
    if len(d) < 15:
        u["skip"] = True; continue
    cl = [x[4] for x in d]
    u["ch7"] = (cl[-1] / cl[-8] - 1) * 100
    u["ch30"] = (cl[-1] / cl[-31] - 1) * 100 if len(cl) > 30 else None
    pk_i = max(range(len(d) - 30 if len(d) > 30 else 0, len(d)), key=lambda i: d[i][2])
    u["peak"] = d[pk_i][2]; u["peak_days_ago"] = len(d) - 1 - pk_i
    u["from_peak"] = (cl[-1] / u["peak"] - 1) * 100
    lo30 = min(x[3] for x in d[-31:])
    u["pump30"] = (u["peak"] / lo30 - 1) * 100
    u["rsi_d"] = rsi(cl) if len(cl) > 20 else None
uni = [u for u in uni if not u.get("skip")]

top = sorted(uni, key=lambda u: -u["ch7"])[:TOP]
top30 = sorted([u for u in uni if u.get("ch30") is not None], key=lambda u: -u["ch30"])[:TOP]
pick = {u["inst"]: u for u in top + top30}.values()

for u in pick:
    h = bars(u["inst"], "4H", 120)
    if len(h) > 30:
        cl = [x[4] for x in h]
        u["e20_4h"] = ema(cl[-60:], 20)
        u["below_e20"] = cl[-1] < u["e20_4h"]
        hs = [x[2] for x in h[-7:-1]]
        u["lower_highs"] = sum(1 for i in range(1, len(hs)) if hs[i] < hs[i - 1])
        u["rsi_4h"] = rsi(cl)
        u["swing_hi"] = max(x[2] for x in h[-13:])
        u["lo_2d"] = min(x[3] for x in h[-13:])
        tr = [max(h[i][2], h[i-1][4]) - min(h[i][3], h[i-1][4]) for i in range(len(h)-14, len(h))]
        u["atr4h"] = sum(tr) / len(tr)
    f = get(f"/api/v5/public/funding-rate?instId={u['inst']}")
    u["fund"] = float(f[0]["fundingRate"]) * 100 if f else None
    oi = get(f"/api/v5/rubik/stat/contracts/open-interest-history?instId={u['inst']}&period=1H&limit=25")
    if len(oi) >= 25:
        oi = sorted(oi, key=lambda x: int(x[0]))
        u["oi24"] = (float(oi[-1][3]) / float(oi[0][3]) - 1) * 100 if float(oi[0][3]) else None
    # rolling-over score: off the peak, below 4h EMA20, falling highs, peak not today
    s = 0
    s += u["from_peak"] <= -8
    s += bool(u.get("below_e20"))
    s += u.get("lower_highs", 0) >= 3
    s += u["peak_days_ago"] >= 2
    u["roll"] = s
    time.sleep(0.1)


def fmt(v, p=1, sign=True):
    return "  -  " if v is None else (f"{v:+.{p}f}" if sign else f"{v:.{p}f}")


hdr = f"{'coin':<9}{'7g%':>7}{'30g%':>8}{'pump30':>8}{'tepe%':>7}{'tepeG':>6}{'rsiG':>6}{'rsi4h':>6}{'<e20':>5}{'LH':>4}{'fund%':>8}{'OI24%':>7}{'hacimM':>8}{'dönüş':>6}"


def table(title, rows):
    print(f"\n== {title} ==\n" + hdr)
    for u in rows:
        print(f"{u['coin']:<9}{fmt(u['ch7']):>7}{fmt(u.get('ch30')):>8}{fmt(u['pump30'],0):>8}{fmt(u['from_peak']):>7}"
              f"{u['peak_days_ago']:>6}{fmt(u.get('rsi_d'),0,False):>6}{fmt(u.get('rsi_4h'),0,False):>6}"
              f"{('E' if u.get('below_e20') else '-'):>5}{u.get('lower_highs','-'):>4}{fmt(u.get('fund'),4):>8}"
              f"{fmt(u.get('oi24')):>7}{u['vol']/1e6:>8.0f}{u.get('roll','-'):>5}/4")


table("7 GÜNDE EN ÇOK ARTANLAR", top)
table("30 GÜNDE EN ÇOK ARTANLAR", top30)
roll = sorted([u for u in pick if u["roll"] >= 3], key=lambda u: (-u["roll"], -u["pump30"]))
table("SHORT ADAYI: pompalanmış + dönüyor (skor>=3)", roll)
print("\nSEVİYELER (4h): fiyat | EMA20 | 2g swing tepe | 2g dip | ATR4h")
for u in roll:
    print(f"{u['coin']:<9}{u['last']:<12g}{u.get('e20_4h',0):<12.5g}{u.get('swing_hi',0):<12g}{u.get('lo_2d',0):<12g}{u.get('atr4h',0):.4g}")
