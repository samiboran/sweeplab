"""Morning brief for the Kaldıraç Gözlem Defteri.

Reads notebook_daily.json (+ latest.json live snapshot), computes a 30-day z-score
for every indicator, applies the alarm rules, gives each of the four layers a
green / yellow / red status, writes today.json and sends the summary to Telegram
(TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID; skipped when either is missing).

Alarm rules
  1. |z| > 2 on any indicator (30-day window; weekly series use the last 12 weeks)
  2. Long/short account ratio > 2.5
  3. Open interest change over the last 24h beyond ±5%, measured in coins
     (USD OI falls with price on its own)
  4. Funding extreme: a day's funding sum > 0.09% or < -0.03%
     (normal is about 0.01% per 8h, i.e. ~0.03% a day)
  5. 7-day correlation more than 0.5 away from the 30-day correlation
  6. Weekly net-liquidity change flipped direction versus the prior week
  7. Squeeze warning: coin OI z > 2 (side read from funding)
  8. Bull regime but daily close below MA50 (came with 5/5 tops, 2/6 corrections)
  9. CPI / FOMC / NFP today or tomorrow (event risk)
Levels block ("likidite olmayalım"): MA50, 20-day high/low, ATR and the leverage
ceiling that keeps liquidation beyond a stop placed half an ATR past the swing.
Positioning is read against the trend: a crowded long book in a bull trend is
"düzeltme riski", in a bear trend "çöküş riski". Each coin also gets the day's
price-vs-OI label (kaldıraçlı yükseliş / short squeeze / yeni short / temizlik).
Layer status: red = any alarm in the layer; yellow = any |z| > 1.5; else green.
"""
import datetime as dt, html, json, math, os, urllib.request

OUT = os.environ.get("OUT_DIR", "data/derivs")
Z_ALARM, Z_WATCH = 2.0, 1.5
LS_MAX, OI_24H_MAX = 2.5, 5.0
FUND_HI, FUND_LO = 0.09, -0.03
CORR_GAP = 0.5


def zscore(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 8:
        return None
    last, mean = vals[-1], sum(vals) / len(vals)
    sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))
    return (last - mean) / sd if sd else None


def get(row, path):
    cur = row
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


# layer, key, label, path in row, display format
INDICATORS = [
    ("regime", "netliq", "Net likidite", None, "T$"),
    ("regime", "real10y", "Reel faiz (10y)", "regime.real10y", "%"),
    ("regime", "dxy", "DXY", "regime.dxy", "num"),
    ("regime", "stables", "Stablecoin arzı", "regime.stables_usd", "B$"),
    ("macro", "gold", "Altın", "macro.gold", "num"),
    ("macro", "gold_cot", "Altın COT fon net", None, "int"),
    ("macro", "gld", "GLD (ton)", "macro.gld_tonnes", "num"),
    ("macro", "wti", "WTI", "macro.wti", "num2"),
    ("macro", "brent", "Brent", "macro.brent", "num2"),
    ("risk", "spx", "S&P 500", "risk.spx", "num"),
    ("risk", "ndx", "Nasdaq", "risk.ndx", "num"),
    ("risk", "vix", "VIX", "risk.vix", "num"),
    ("risk", "hy", "HY spread", "risk.hy_oas", "%"),
    ("pos", "btc_oi", "BTC açık poz. (coin)", "pos.btc.oi_coin", "coin"),
    ("pos", "eth_oi", "ETH açık poz. (coin)", "pos.eth.oi_coin", "coin"),
    ("pos", "btc_fund", "BTC funding", "pos.btc.funding_sum_pct", "pct3"),
    ("pos", "eth_fund", "ETH funding", "pos.eth.funding_sum_pct", "pct3"),
    ("pos", "btc_ls", "BTC L/S", "pos.btc.ls_ratio", "num2"),
    ("pos", "eth_ls", "ETH L/S", "pos.eth.ls_ratio", "num2"),
    ("pos", "btc_cot", "CME BTC fon net", None, "int"),
    ("corr", "btc_spx", "BTC–S&P", "corr.btc_spx", "num2"),
    ("corr", "btc_ndx", "BTC–Nasdaq", "corr.btc_ndx", "num2"),
    ("corr", "btc_dxy", "BTC–DXY", "corr.btc_dxy", "num2"),
    ("corr", "btc_eth", "BTC–ETH", "corr.btc_eth", "num2"),
    ("corr", "btc_gold", "BTC–Altın", "corr.btc_gold", "num2"),
    ("corr", "eth_gold", "ETH–Altın", "corr.eth_gold", "num2"),
]
LAYERS = {"regime": "Rejim", "risk": "Risk iştahı", "pos": "Pozisyon", "macro": "Altın & Makro", "corr": "Korelasyonlar"}


def fmt(v, kind):
    if v is None:
        return "–"
    if kind == "T$":
        return f"{v / 1e6:.2f} T$"
    if kind == "B$":
        return f"{v / 1e9:.1f} B$" if v < 1e12 else f"{v / 1e9:,.0f} B$"
    if kind == "%":
        return f"%{v:.2f}"
    if kind == "pct3":
        return f"%{v:.3f}"
    if kind == "num2":
        return f"{v:.2f}"
    if kind == "int":
        return f"{v:,.0f}"
    if kind == "coin":
        return f"{v / 1e6:.2f}M" if v >= 1e6 else f"{v / 1e3:.1f}K"
    return f"{v:,.2f}" if v < 1000 else f"{v:,.0f}"


def live_oi_24h(coin, col):
    """OI change over the last 24 hours from the hourly OKX USDT-perp snapshot.
    col 2 = OI in coins (oiCcy), col 3 = OI in USD."""
    try:
        snap = json.load(open(f"{OUT}/latest.json"))["sources"][f"okx_{coin}"]["oi_hist_1h"]
        data = snap["data"]["data"] if isinstance(snap["data"], dict) else snap["data"]
        data = sorted(data, key=lambda x: int(x[0]))
        now, ts_now = float(data[-1][col]), int(data[-1][0])
        target = ts_now - 24 * 3600 * 1000
        prev = min(data, key=lambda x: abs(int(x[0]) - target))
        if abs(int(prev[0]) - target) > 2 * 3600 * 1000:
            return None
        return (now / float(prev[col]) - 1) * 100
    except Exception:
        return None


WATCH = ("sol", "xrp", "doge", "pump")
WATCH_OI_24H = 10.0  # alts move more; a wider band than BTC/ETH's 5%


def latest_oi_usd(coin):
    try:
        snap = json.load(open(f"{OUT}/latest.json"))["sources"][f"okx_{coin}"]["oi_hist_1h"]
        data = snap["data"]["data"] if isinstance(snap["data"], dict) else snap["data"]
        return float(max(data, key=lambda x: int(x[0]))[3])
    except Exception:
        return None


LEV_BUFFER_ATR = 0.5   # stop sits half an ATR beyond the 20-day swing (where the crowd's stops are)
LEV_SAFETY = 0.8       # keep liquidation 20% further than the stop (maintenance margin, fees, wicks)
NEAR_MA50_PCT = 2.0
EVENT_NAMES = {"CPI": "ABD enflasyonu (CPI)", "FOMC": "Fed faiz kararı (FOMC)", "NFP": "ABD istihdam (NFP)"}
EVENT_TIME = {"CPI": "15:30", "NFP": "15:30", "FOMC": "21:00"}  # Istanbul


def levels_and_risk(out, rows, calendar):
    """'Likidite olmayalım' block: key levels and the leverage that keeps a position's
    liquidation beyond them.

    - MA50 in a bull regime: in our top-vs-correction study a daily close below MA50
      came with 5/5 tops but only 2/6 corrections -> alarm, with the streak length.
    - 20-day high/low: obvious swing levels where stops and liquidation clusters sit.
    - Max leverage: the stop goes half an ATR past the swing; liquidation must be
      beyond the stop with a 20% margin -> lev = 0.8 / stop distance.
    - Macro event today/tomorrow (CPI, FOMC, NFP): event-risk alarm.
    """
    out["levels"] = {}
    for c in ("btc", "eth"):
        C = c.upper()
        days = [r["pos"].get(c) or {} for r in rows]
        if len(days) < 21 or not days[-1].get("close"):
            continue
        tr = rows[-1]["regime"].get("trend_" + c) or {}
        close, ma50, ma200 = days[-1]["close"], tr.get("ma50"), tr.get("ma200")
        hi20 = max(d["high"] for d in days[-20:] if d.get("high"))
        lo20 = min(d["low"] for d in days[-20:] if d.get("low"))
        trs = [max(d["high"], p["close"]) - min(d["low"], p["close"]) for p, d in zip(days[-15:-1], days[-14:])]
        atr = sum(trs) / len(trs)
        long_stop, short_stop = lo20 - LEV_BUFFER_ATR * atr, hi20 + LEV_BUFFER_ATR * atr
        long_dist, short_dist = (close - long_stop) / close, (short_stop - close) / close
        # how many consecutive daily closes below MA50 (MA50 per day from the rows we have)
        closes = [d.get("close") for d in days]
        streak = 0
        for i in range(len(closes) - 1, 49, -1):
            if closes[i] < sum(closes[i - 49:i + 1]) / 50:
                streak += 1
            else:
                break
        if ma50 and closes[-1] < ma50 and streak == 0:
            streak = 1
        lv = {"close": close, "ma50": ma50, "ma200": ma200,
              "d50_pct": round((close / ma50 - 1) * 100, 2) if ma50 else None,
              "hi20": hi20, "lo20": lo20, "atr": round(atr, 2), "atr_pct": round(atr / close * 100, 2),
              "long_stop": round(long_stop, 2), "short_stop": round(short_stop, 2),
              "long_stop_pct": round(long_dist * 100, 2), "short_stop_pct": round(short_dist * 100, 2),
              "max_lev_long": max(1, math.floor(LEV_SAFETY / long_dist)) if long_dist > 0 else None,
              "max_lev_short": max(1, math.floor(LEV_SAFETY / short_dist)) if short_dist > 0 else None,
              "below_ma50_days": streak}
        out["levels"][c] = lv
        if ma50 and close < ma50 and tr.get("state") == "boga":
            out["alarms"].append({"layer": "regime", "rule": "ma50",
                                  "text": f"{C} günlük kapanış 50 günlük ortalamanın altında ({close:,.0f} < {ma50:,.0f}, {streak} gündür). "
                                          "Zirve araştırmasında 5/5 zirvede görüldü, düzeltmelerde 2/6: long kaldıracını azalt, "
                                          "MA50 geri alınana kadar yeni long'u küçük tut."})

    report_day = dt.date.fromisoformat(out["date"]) + dt.timedelta(days=1)
    for kind, dates in calendar.items():
        for when, d in (("Bugün", report_day), ("Yarın", report_day + dt.timedelta(days=1))):
            if d.isoformat() in dates:
                out["alarms"].append({"layer": "macro", "rule": "event",
                                      "text": f"{when} {EVENT_NAMES.get(kind, kind)} ({EVENT_TIME.get(kind, '')} İstanbul): veri anında iki yönde iğne gelir, "
                                              "likidite bantları süpürülür. Veriden önce yeni pozisyon açma, açık pozisyonda kaldıracı düşür, "
                                              "stopu 20 günlük uçların ötesine koy."})


STOCK_PLAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_plan.json")


def stock_plans():
    """Price-level plan for stocks the user holds (tools/stock_plan.json): dip-buy levels
    and breakout-add levels, checked against Yahoo daily candles."""
    try:
        plan = json.load(open(STOCK_PLAN))
    except Exception:
        return {}, []
    out, alarms = {}, []
    for sym, p in plan.items():
        try:
            req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=3mo&interval=1d",
                                         headers={"User-Agent": "Mozilla/5.0"})
            res = json.loads(urllib.request.urlopen(req, timeout=20).read())["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            bars = [(dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat(), h, l, c)
                    for t, h, l, c in zip(res["timestamp"], q["high"], q["low"], q["close"]) if c is not None]
        except Exception as e:
            out[sym] = {"name": p.get("name", sym), "error": str(e)[:120]}
            continue
        d, hi, lo, close = bars[-1]
        prev = bars[-2][3] if len(bars) > 1 else None
        closes = [b[3] for b in bars]
        ma20 = sum(closes[-20:]) / min(20, len(closes))
        x = {"name": p.get("name", sym), "date": d, "close": round(close, 2), "high": round(hi, 2), "low": round(lo, 2),
             "chg_pct": round((close / prev - 1) * 100, 2) if prev else None, "ma20": round(ma20, 2),
             "hi3m": round(max(b[1] for b in bars), 2), "lo3m": round(min(b[2] for b in bars), 2),
             "levels": [], "notes": p.get("notes")}
        for lv in p.get("buy_dips", []):
            hit = lo <= lv
            x["levels"].append({"kind": "dip", "price": lv, "dist_pct": round((lv / close - 1) * 100, 1), "hit": hit})
            if hit:
                alarms.append(f"{x['name']} ({sym}) alım seviyesine indi: {lv} (gün dibi {lo:.2f}, kapanış {close:.2f}). Planlı ekleme zamanı; tek seferde değil, parça parça.")
        for lv in p.get("breakout_adds", []):
            hit = close >= lv
            x["levels"].append({"kind": "breakout", "price": lv, "dist_pct": round((lv / close - 1) * 100, 1), "hit": hit})
            if hit:
                alarms.append(f"{x['name']} ({sym}) {lv} üstünde kapattı ({close:.2f}): kırılım eklemesi. Ertesi gün {lv} üstünde kalırsa teyit.")
        out[sym] = x
    return out, alarms


def band_check(rows):
    """Which of yesterday's estimated liquidation bands did the last full day sweep,
    and did price close back beyond them (sweep + reclaim) or not. Appends to
    OUT_DIR/band_log.csv so hit rates can be counted later."""
    last = rows[-1]
    day = last["date"]
    try:
        lm = json.load(open(f"{OUT}/liq_maps/{day}.json"))
    except Exception:
        return []
    res, log = [], []
    for c, m in lm.get("coins", {}).items():
        p = (last.get("pos") or {}).get(c) or {}
        hi, lo, cl = p.get("high"), p.get("low"), p.get("close")
        if not (hi and lo and cl) or m.get("error"):
            continue
        for side, key in (("long", "long_bands"), ("short", "short_bands")):
            for bnd in m.get(key) or []:
                px = bnd["price"]
                swept = lo <= px if side == "long" else hi >= px
                reclaimed = swept and (cl > px if side == "long" else cl < px)
                log.append([day, c, side, round(px, 4), bnd.get("lev"), bnd.get("dist_pct"), int(swept), int(reclaimed), cl])
                if swept:
                    res.append({"coin": c, "side": side, "price": px, "lev": bnd.get("lev"), "reclaimed": reclaimed, "close": cl})
    try:
        path = f"{OUT}/band_log.csv"
        old = open(path).read().splitlines() if os.path.exists(path) else ["date,coin,side,band,lev,dist_pct,swept,reclaimed,close"]
        old = [l for l in old if not l.startswith(day + ",")] + [",".join(map(str, x)) for x in log]
        open(path, "w").write("\n".join(old) + "\n")
    except Exception:
        pass
    return res


def build():
    nb = json.load(open(f"{OUT}/notebook_daily.json"))
    rows, weekly = nb["rows"], nb["weekly"]
    last = rows[-1]
    out = {"date": last["date"], "built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "layers": {}, "alarms": [], "indicators": {}}

    for layer, key, label, path, kind in INDICATORS:
        if key == "netliq":
            series = [v for _, v in weekly["netliq_musd"]][-12:]
            asof = weekly["netliq_musd"][-1][0] if weekly["netliq_musd"] else None
        elif key == "gold_cot":
            series = [v for _, v in weekly.get("cot_gold_mm_net", [])][-12:]
            asof = weekly["cot_gold_mm_net"][-1][0] if weekly.get("cot_gold_mm_net") else None
        elif key == "btc_cot":
            series = [v for _, v in weekly["cot_btc_lev_net"]][-12:]
            asof = weekly["cot_btc_lev_net"][-1][0] if weekly["cot_btc_lev_net"] else None
        else:
            series = [get(r, path) for r in rows[-30:]]  # z-score window stays 30 days
            asof = get(last, path.rsplit(".", 1)[0] + "." + path.rsplit(".", 1)[1].split("_")[0] + "_asof") if layer in ("regime", "risk", "macro") else last["date"]
        val = series[-1] if series else None
        z = zscore(series)
        out["indicators"][key] = {"layer": layer, "label": label, "value": val, "display": fmt(val, kind),
                                  "z": None if z is None else round(z, 2), "asof": asof}
        if z is not None and abs(z) > Z_ALARM and not (key in ("btc_oi", "eth_oi") and z > 0):  # high OI -> squeeze warning below
            yön = "yüksek" if z > 0 else "düşük"
            out["alarms"].append({"layer": layer, "rule": "z", "text": f"{label} 30 günlük ortalamasından {abs(z):.1f} std {yön} ({fmt(val, kind)})"})

    pos = last["pos"]
    # Squeeze warning: swollen coin OI preceded bigger 7-day moves in 2022-23 (median 11.4%
    # vs 7.2%), direction a coin flip; with high funding as well, 5 of 8 cases fell.
    # A caution flag, not a trade signal (the effect faded in 2024-26).
    for c in ("btc", "eth"):
        z = out["indicators"][c + "_oi"]["z"]
        f = (pos.get(c) or {}).get("funding_sum_pct")
        if z is not None and z > Z_ALARM:
            side = (" Funding de yüksek: long tarafı kırılgan." if f is not None and f > 0.03 else
                    " Funding negatif: short tarafı kırılgan." if f is not None and f < 0 else " Yön belirsiz.")
            out["alarms"].append({"layer": "pos", "rule": "squeeze",
                                  "text": f"{c.upper()} squeeze riski: açık pozisyon şişkin (z {z:.1f}), sert hareket ihtimali yüksek.{side} Dar stop ve ek kaldıraçtan kaçın."})
    for c in ("btc", "eth"):
        C = c.upper()
        ls = (pos.get(c) or {}).get("ls_ratio")
        if ls is not None and ls > LS_MAX:
            out["alarms"].append({"layer": "pos", "rule": "ls", "text": f"{C} long/short hesap oranı {ls:.2f} (>{LS_MAX}): kalabalık long'da"})
        # Alarm on coin-denominated OI: USD OI drops by itself when price drops.
        oi24, src = live_oi_24h(C, 2), "son 24 saat"
        oi24_usd = live_oi_24h(C, 3)
        if oi24 is None:
            oi24, src = (pos.get(c) or {}).get("oi_coin_chg_pct"), "dünkü gün"
            oi24_usd = (pos.get(c) or {}).get("oi_chg_pct")
        ind = out["indicators"][c + "_oi"]
        ind["chg24"] = None if oi24 is None else round(oi24, 2)
        ind["chg24_usd"] = None if oi24_usd is None else round(oi24_usd, 2)
        ind["usd"] = (pos.get(c) or {}).get("oi_usd")
        if oi24 is not None and abs(oi24) > OI_24H_MAX:
            yön = "arttı" if oi24 > 0 else "düştü"
            out["alarms"].append({"layer": "pos", "rule": "oi24", "text": f"{C} açık pozisyon {src} coin bazında %{abs(oi24):.1f} {yön}"})
        f = (pos.get(c) or {}).get("funding_sum_pct")
        if f is not None and (f > FUND_HI or f < FUND_LO):
            yön = "aşırı pozitif (long'lar pahalı ödüyor)" if f > 0 else "negatif (short'lar ödüyor)"
            out["alarms"].append({"layer": "pos", "rule": "funding", "text": f"{C} funding uç değerde: günlük %{f:.3f}, {yön}"})

    for k, label in (("btc_spx", "BTC–S&P"), ("btc_ndx", "BTC–Nasdaq"), ("btc_dxy", "BTC–DXY"), ("btc_eth", "BTC–ETH"),
                     ("btc_gold", "BTC–Altın"), ("eth_gold", "ETH–Altın")):
        c30, c7 = last["corr"].get(k), last["corr"].get(k + "_7d")
        out["indicators"][k]["corr7"] = None if c7 is None else round(c7, 2)
        if c30 is not None and c7 is not None and abs(c7 - c30) > CORR_GAP:
            out["alarms"].append({"layer": "corr", "rule": "corr", "text": f"{label} korelasyonu kırıldı: 7 gün {c7:+.2f}, 30 gün {c30:+.2f}"})

    nl = weekly["netliq_musd"]
    if len(nl) >= 3:
        d1, d0 = nl[-1][1] - nl[-2][1], nl[-2][1] - nl[-3][1]
        out["indicators"]["netliq"]["wk_chg"] = round(d1 / 1e3, 1)  # USD billions
        if d1 * d0 < 0:
            yön = "artışa" if d1 > 0 else "düşüşe"
            out["alarms"].append({"layer": "regime", "rule": "netliq_flip", "text": f"Net likidite yön değiştirdi: bu hafta {yön} geçti ({d1 / 1e3:+.0f} B$, {nl[-1][0]})"})

    out["macro_ctx"] = {k: last.get("macro", {}).get(k) for k in ("gold_from_high_pct", "gold_high120_date", "gold_src", "cot_gold_mm_net_wk_chg", "gld_7d_chg_t")}

    # Trend (regime) and a positioning read that depends on it
    out["coins"] = {}
    for c in ("btc", "eth"):
        tr = last["regime"].get("trend_" + c) or {}
        p = pos.get(c) or {}
        ls, f = p.get("ls_ratio"), p.get("funding_sum_pct")
        ls_z = out["indicators"][c + "_ls"]["z"]
        crowded_long = (ls is not None and ls > LS_MAX) or (ls_z is not None and ls_z > Z_ALARM) or (f is not None and f > FUND_HI)
        crowded_short = f is not None and f < FUND_LO
        st = tr.get("state")
        if crowded_long:
            risk = {"boga": "long kalabalığı → düzeltme riski", "ayi": "long kalabalığı → çöküş riski"}.get(
                st, "long kalabalığı → kırılgan zemin, sert hareket riski")
        elif crowded_short:
            risk = "short kalabalığı → squeeze riski"
        else:
            risk = "pozisyonlanma dengeli"
        out["coins"][c] = {"trend": st, "trend_text": TREND[st], "dist200_pct": tr.get("dist200_pct"),
                           "ma50": tr.get("ma50"), "ma200": tr.get("ma200"), "close": tr.get("close"),
                           "flow": p.get("flow"), "flow_text": FLOW.get(p.get("flow"), "–"),
                           "crowded_long": crowded_long, "crowded_short": crowded_short, "reading": risk}

    # Watch list (SOL, XRP, DOGE, PUMP): kept small. Only alarms reach the message;
    # they do not change the four layer colours.
    out["watch"], out["watch_alarms"] = {}, []
    caps = {}
    try:
        cg = json.load(open(f"{OUT}/latest.json"))["sources"].get("coingecko", {})
        caps = cg.get("data", {}) if cg.get("ok") else {}
    except Exception:
        pass
    for c in WATCH:
        C = c.upper()
        rows_c = [r["pos"].get(c) for r in rows[-30:] if r.get("pos", {}).get(c)]
        if not rows_c:
            continue
        p = rows_c[-1]
        z = zscore([r.get("oi_coin") for r in rows_c])
        oi24, oi24_usd = live_oi_24h(C, 2), live_oi_24h(C, 3)
        if oi24 is None:
            oi24, oi24_usd = p.get("oi_coin_chg_pct"), p.get("oi_chg_pct")
        oi_usd = latest_oi_usd(C) or p.get("oi_usd")
        mcap = (caps.get(C) or {}).get("market_cap")
        f, ls = p.get("funding_sum_pct"), p.get("ls_ratio")
        w = {"close": p.get("close"), "chg_pct": p.get("chg_pct"), "oi_coin": p.get("oi_coin"), "oi_usd": oi_usd,
             "oi_z": None if z is None else round(z, 2), "oi24": None if oi24 is None else round(oi24, 2),
             "oi24_usd": None if oi24_usd is None else round(oi24_usd, 2),
             "oi_mcap_pct": round(oi_usd / mcap * 100, 2) if oi_usd and mcap else None,
             "funding": f, "ls": ls, "flow": p.get("flow"), "flow_text": FLOW.get(p.get("flow"), "–"), "alarms": []}
        if z is not None and z > Z_ALARM:
            side = (" Funding yüksek: long tarafı kırılgan." if f is not None and f > 0.03 else
                    " Funding negatif: short tarafı kırılgan." if f is not None and f < 0 else "")
            w["alarms"].append(f"{C} squeeze riski: açık pozisyon şişkin (z {z:.1f}).{side}")
        if oi24 is not None and abs(oi24) > WATCH_OI_24H:
            w["alarms"].append(f"{C} açık pozisyon 24 saatte coin bazında %{abs(oi24):.0f} {'arttı' if oi24 > 0 else 'düştü'}")
        if ls is not None and ls > LS_MAX:
            w["alarms"].append(f"{C} long/short hesap oranı {ls:.2f}")
        if f is not None and (f > FUND_HI or f < FUND_LO):
            w["alarms"].append(f"{C} funding uç değerde: günlük %{f:.3f}")
        out["watch"][c] = w
        out["watch_alarms"] += w["alarms"]

    levels_and_risk(out, rows, nb["calendar"])
    out["stocks"], out["stock_alarms"] = stock_plans()
    out["band_sweeps"] = band_check(rows)
    try:
        lm = json.load(open(f"{OUT}/liq_map.json"))
        out["liq_map"] = {"built_utc": lm.get("built_utc"),
                          "coins": {c: {k: v.get(k) for k in ("price", "long_bands", "short_bands", "error")}
                                    for c, v in lm.get("coins", {}).items()}}
    except Exception:
        out["liq_map"] = None
    eb = [(r["date"], r["pos"]["eth"]["close"] / r["pos"]["btc"]["close"]) for r in rows
          if (r["pos"].get("eth") or {}).get("close") and (r["pos"].get("btc") or {}).get("close")]
    sb = [(r["date"], r["pos"]["sol"]["close"] / r["pos"]["btc"]["close"]) for r in rows
          if (r["pos"].get("sol") or {}).get("close") and (r["pos"].get("btc") or {}).get("close")]
    out["ratios"] = {}
    for k, ser in (("eth_btc", eb), ("sol_btc", sb)):
        if len(ser) >= 30:
            v = [x for _, x in ser]
            out["ratios"][k] = {"value": round(v[-1], 6), "hi30": round(max(v[-30:]), 6), "lo30": round(min(v[-30:]), 6),
                                "chg30_pct": round((v[-1] / v[-30] - 1) * 100, 2), "ma20": round(sum(v[-20:]) / 20, 6)}

    for layer, name in LAYERS.items():
        zs = [i["z"] for i in out["indicators"].values() if i["layer"] == layer and i["z"] is not None]
        al = [a for a in out["alarms"] if a["layer"] == layer]
        st = "red" if al else ("yellow" if any(abs(z) > Z_WATCH for z in zs) else "green")
        out["layers"][layer] = {"name": name, "status": st, "alarms": len(al)}

    today = dt.date.fromisoformat(out["date"]) + dt.timedelta(days=1)
    upcoming = []
    for kind, dates in nb["calendar"].items():
        for d in dates:
            if today.isoformat() <= d <= (today + dt.timedelta(days=14)).isoformat():
                upcoming.append({"date": d, "event": kind})
    out["upcoming"] = sorted(upcoming, key=lambda x: x["date"])
    out["today_events"] = [k for k, ds in nb["calendar"].items() if today.isoformat() in ds]
    out["report_day"] = today.isoformat()
    return out


DOT = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
TREND = {"boga": "Boğa", "ayi": "Ayı", "gecis": "Geçiş", None: "–"}
FLOW = {"kaldiracli_yukselis": "Kaldıraçlı yükseliş (fiyat↑ OI↑)", "short_squeeze": "Short squeeze (fiyat↑ OI↓)",
        "yeni_short": "Yeni short (fiyat↓ OI↑)", "temizlik": "Temizlik (fiyat↓ OI↓)", "yatay": "Yatay / sakin",
        "oi_sabit": "OI sabit (fiyat oynadı, pozisyon değişmedi)", None: "–"}


def message(b):
    ind = b["indicators"]
    gun = dt.date.fromisoformat(b["report_day"]).strftime("%d.%m.%Y")
    lines = [f"<b>Kaldıraç Gözlem Defteri · {gun}</b>"]
    if b["today_events"]:
        lines.append("📅 Bugün: <b>" + ", ".join(f"{k} {EVENT_TIME.get(k, '')}" for k in b["today_events"]) + "</b> (İstanbul)")
    lines.append("")
    co = b["coins"]
    for layer, info in b["layers"].items():
        lines.append(f"{DOT[info['status']]} <b>{info['name']}</b>")
        if layer == "regime":
            for c in ("btc", "eth"):
                x = co[c]
                d = "" if x["dist200_pct"] is None else f", 200g ort. {x['dist200_pct']:+.1f}%"
                lines.append(f"   {c.upper()} trend: {x['trend_text']}{d}")
        if layer == "pos":
            for c in ("btc", "eth"):
                x = co[c]
                lines.append(f"   {c.upper()}: {x['flow_text']} · {x['reading']}")
    lines.append("")
    for c in ("btc", "eth"):
        o = ind[c + "_oi"]
        lines.append(f"{c.upper()} OI {o['display']} {c.upper()} (24s coin {_s(o.get('chg24'))}, $ {_s(o.get('chg24_usd'))}) · L/S {ind[c + '_ls']['display']} · funding {ind[c + '_fund']['display']}")
    m = b.get("macro_ctx") or {}
    lines.append(f"Altın {ind['gold']['display']}" + (f" (120g zirveden {m['gold_from_high_pct']:+.1f}%)" if m.get("gold_from_high_pct") is not None else "")
                 + f" · WTI {ind['wti']['display']} · Brent {ind['brent']['display']}")
    lines.append(f"VIX {ind['vix']['display']} · HY {ind['hy']['display']} · DXY {ind['dxy']['display']} · Reel faiz {ind['real10y']['display']}")
    lv = b.get("levels") or {}
    if lv:
        lines.append("")
        lines.append("<b>Seviyeler · likidite olmayalım</b>")
        for c, x in lv.items():
            ma = f"MA50 {x['ma50']:,.0f} ({x['d50_pct']:+.1f}%)" if x.get("ma50") else ""
            lines.append(f"{c.upper()} {x['close']:,.0f} · {ma} · 20g {x['lo20']:,.0f}–{x['hi20']:,.0f} · ATR %{x['atr_pct']:.1f}")
            lines.append(f"   Long: stop &lt;{x['long_stop']:,.0f} (−%{x['long_stop_pct']:.1f}) → tavan {x['max_lev_long']}x · "
                         f"Short: stop &gt;{x['short_stop']:,.0f} (+%{x['short_stop_pct']:.1f}) → tavan {x['max_lev_short']}x")
        lm = (b.get("liq_map") or {}).get("coins") or {}
        for c in ("btc", "eth"):
            m = lm.get(c) or {}
            if m.get("long_bands") or m.get("short_bands"):
                f = lambda bs: ", ".join(f"{x['price']:,.0f} ({x['lev']}x)" for x in bs[:3]) or "–"
                lines.append(f"   {c.upper()} tahmini likidasyon: long ↓ {f(m.get('long_bands') or [])} · short ↑ {f(m.get('short_bands') or [])}")
        bs = b.get("band_sweeps") or []
        if bs:
            f2 = lambda x: f"{x['coin'].upper()} {x['side']} {x['price']:,.{2 if x['price'] < 100 else 0}f} ({x['lev']}x) " + ("→ geri alındı" if x["reclaimed"] else "→ geri alınmadı")
            lines.append("   Dün süpürülen bantlar: " + " · ".join(f2(x) for x in bs))
        r = b.get("ratios") or {}
        if r.get("eth_btc"):
            x = r["eth_btc"]
            lines.append(f"   ETH/BTC {x['value']:.4f} (30g {x['chg30_pct']:+.1f}%, aralık {x['lo30']:.4f}–{x['hi30']:.4f})")
        lines.append("   <i>Tavan: bunun üstünde stoptan önce likide olursun. Boyutu kaldıraç değil risk belirler: işlem başı hesabın en fazla %1'i.</i>")
    st = b.get("stocks") or {}
    if st:
        lines.append("")
        lines.append("<b>Hisse planı</b>")
        for sym, x in st.items():
            if x.get("error"):
                lines.append(f"{x['name']} ({sym}): veri alınamadı")
                continue
            lv = " · ".join(f"{'al' if l['kind'] == 'dip' else 'ekle↑'} {l['price']:g} ({l['dist_pct']:+.1f}%)" for l in x["levels"])
            chg = f" ({x['chg_pct']:+.1f}%)" if x.get("chg_pct") is not None else ""
            lines.append(f"{x['name']} {x['close']:.2f}{chg} · {lv}")
        for a in b.get("stock_alarms") or []:
            lines.append("⚠️ " + html.escape(a))
    if b["alarms"]:
        lines.append("")
        lines.append("<b>Alarmlar</b>")
        for a in b["alarms"]:
            lines.append("• " + html.escape(a["text"]))
    else:
        lines.append("")
        lines.append("Alarm yok.")
    wa = b.get("watch_alarms") or []
    if b.get("watch"):
        lines.append("")
        if wa:
            lines.append("<b>Altcoin izleme</b>")
            for a in wa:
                lines.append("• " + html.escape(a))
        else:
            lines.append("Altcoin izleme (" + ", ".join(k.upper() for k in b["watch"]) + "): sakin.")
    if b["upcoming"]:
        lines.append("")
        lines.append("Yaklaşan: " + ", ".join(f"{x['event']} {dt.date.fromisoformat(x['date']).strftime('%d.%m')}" for x in b["upcoming"]))
    return "\n".join(lines)


def _s(v):
    return "–" if v is None else f"{v:+.1f}%"


def send(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram secrets missing; message not sent.")
        return False
    body = json.dumps({"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        ok = json.loads(r.read()).get("ok")
    print("Telegram sent:", ok)
    return ok


if __name__ == "__main__":
    brief = build()
    text = message(brief)
    brief["message"] = text
    json.dump(brief, open(f"{OUT}/today.json", "w"), indent=1, ensure_ascii=False)
    print(text)
    if os.environ.get("SEND_TELEGRAM", "1") == "1":
        send(text)
