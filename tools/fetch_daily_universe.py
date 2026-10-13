"""Daily OKX USDT-perp candles (as far back as available) for a fixed large-cap
universe, one CSV per coin, for local research. Output: OUT/candles_1d/<COIN>.csv"""
import json, os, time, urllib.request

OUT = os.environ.get("OUT_DIR", "feed/data/research")
COINS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX", "LINK", "DOT", "LTC", "BCH", "NEAR", "APT",
         "UNI", "AAVE", "ARB", "OP", "SUI", "TRX", "HYPE", "ENA", "WLD", "TON", "INJ", "TIA", "FIL", "ATOM", "ETC", "XLM"]


def get(path):
    for a in range(4):
        try:
            req = urllib.request.Request("https://www.okx.com" + path, headers={"User-Agent": "Mozilla/5.0"})
            j = json.loads(urllib.request.urlopen(req, timeout=20).read())
            if str(j.get("code")) == "0":
                return j["data"]
            return []
        except Exception:
            time.sleep(1 + a)
    return []


os.makedirs(f"{OUT}/candles_1d", exist_ok=True)
for coin in COINS:
    inst, rows, after = f"{coin}-USDT-SWAP", {}, None
    for _ in range(30):
        d = get(f"/api/v5/market/history-candles?instId={inst}&bar=1Dutc&limit=100" + (f"&after={after}" if after else ""))
        if not d:
            break
        for x in d:
            if len(x) < 9 or x[8] == "1":
                rows[int(x[0])] = x[:6]
        after = min(int(x[0]) for x in d)
        time.sleep(0.12)
    if rows:
        with open(f"{OUT}/candles_1d/{coin}.csv", "w") as f:
            f.write("ts,open,high,low,close,vol\n")
            for k in sorted(rows):
                f.write(",".join(rows[k]) + "\n")
    print(coin, len(rows))
