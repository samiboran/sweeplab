"""Piyasa Hava Durumu — chart data (S5). Private engine; output is derived only.

Writes data/site/charts.json:
  crypto.btc / crypto.eth : last 365 daily closes (UTC) with 50/200-day averages
                            (OKX daily candles, longer history from research candles if present)
  macro                   : every history.csv day: raw score, published level, mode, rules version
  version_boundaries      : first day of each rules version
Rounded values only; no OHLC, volume or positioning data.
"""
import csv, datetime as dt, json, os

FEED = os.environ.get("FEED_DIR", "data")
OUT_DIR = os.environ.get("OUT_DIR", os.path.join(FEED, "derivs"))
SITE_OUT = os.environ.get("SITE_OUT", os.path.join(FEED, "site"))
RESEARCH = os.environ.get("RESEARCH_DIR", os.path.join(FEED, "research", "candles_1d"))
DAYS = 365
MACRO_FROM = "2026-10-01"   # Boran: our own macro record is shown from October 2026 (data kept since then)
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri, CC BY 4.0"


def day(ms):
    return dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc).strftime("%Y-%m-%d")


def okx_closes(raw_path, coin):
    """{date: close} from okx_history_raw.json (confirmed daily candles only)."""
    try:
        c = json.load(open(raw_path, encoding="utf-8"))[coin.upper()]["candles"]
        rows = c.get("data") if isinstance(c, dict) else c
        out = {}
        for r in rows or []:
            if len(r) > 8 and str(r[8]) == "0":     # unconfirmed (still forming) candle
                continue
            out[day(r[0])] = float(r[4])
        return out
    except Exception:
        return {}


def research_closes(coin):
    path = os.path.join(RESEARCH, coin.upper() + ".csv")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return {day(r["ts"]): float(r["close"]) for r in csv.DictReader(fh) if r.get("close")}


def with_ma(closes, days=DAYS, nd=2):
    d = sorted(closes)
    v = [closes[x] for x in d]
    out = []
    for i in range(max(0, len(d) - days), len(d)):
        m50 = sum(v[i - 49:i + 1]) / 50 if i >= 49 else None
        m200 = sum(v[i - 199:i + 1]) / 200 if i >= 199 else None
        rd = lambda x: None if x is None else round(x, nd)
        out.append([d[i], rd(v[i]), rd(m50), rd(m200)])
    return out


def macro(history_path):
    if not os.path.exists(history_path):
        return [], []
    with open(history_path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    out, bounds, seen = [], [], set()
    for r in rows:
        if r["date"] < MACRO_FROM:
            continue
        out.append([r["date"], int(r["raw_score"]), r["level"].upper(), r["mode"], r["rules_version"]])
        if r["rules_version"] not in seen:
            seen.add(r["rules_version"])
            bounds.append({"date": r["date"], "rules_version": r["rules_version"]})
    return out, bounds


def build(raw_path, history_path, now=None):
    now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    crypto = {}
    for coin, nd in (("btc", 0), ("eth", 2)):
        closes = research_closes(coin)
        closes.update(okx_closes(raw_path, coin))     # OKX daily feed wins on overlap (fresher)
        if closes:
            s = with_ma(closes, nd=nd)
            crypto[coin] = {"asof": s[-1][0], "unit": "USDT", "series": s}
    m, bounds = macro(history_path)
    return {"schema": "phd.charts/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
            "generated_at": now, "attribution": ATTRIBUTION, "license": "CC BY 4.0 (türetilmiş değerler)",
            "fields": {"crypto": "[tarih, kapanış, 50g ort., 200g ort.]",
                       "macro": "[tarih, ham skor, yayımlanan seviye, mod, kural sürümü]"},
            "crypto": crypto, "macro": m, "version_boundaries": bounds}


def main():
    rec = build(os.path.join(OUT_DIR, "okx_history_raw.json"), os.path.join(SITE_OUT, "history.csv"))
    os.makedirs(SITE_OUT, exist_ok=True)
    path = os.path.join(SITE_OUT, "charts.json")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(path + ".tmp", path)
    print("charts.json:", {k: len(v["series"]) for k, v in rec["crypto"].items()}, "macro", len(rec["macro"]))


if __name__ == "__main__":
    main()
