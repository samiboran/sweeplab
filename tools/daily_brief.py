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
            series = [get(r, path) for r in rows]
            asof = get(last, path.rsplit(".", 1)[0] + "." + path.rsplit(".", 1)[1].split("_")[0] + "_asof") if layer in ("regime", "risk", "macro") else last["date"]
        val = series[-1] if series else None
        z = zscore(series)
        out["indicators"][key] = {"layer": layer, "label": label, "value": val, "display": fmt(val, kind),
                                  "z": None if z is None else round(z, 2), "asof": asof}
        if z is not None and abs(z) > Z_ALARM:
            yön = "yüksek" if z > 0 else "düşük"
            out["alarms"].append({"layer": layer, "rule": "z", "text": f"{label} 30 günlük ortalamasından {abs(z):.1f} std {yön} ({fmt(val, kind)})"})

    pos = last["pos"]
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
        lines.append("📅 Bugün: <b>" + ", ".join(b["today_events"]) + "</b> (15:30 İstanbul)")
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
    if b["alarms"]:
        lines.append("")
        lines.append("<b>Alarmlar</b>")
        for a in b["alarms"]:
            lines.append("• " + html.escape(a["text"]))
    else:
        lines.append("")
        lines.append("Alarm yok.")
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
