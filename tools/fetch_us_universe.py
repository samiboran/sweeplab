"""Daily Yahoo candles (5y) for a liquid US momentum universe -> OUT/us_1d/<TICKER>.csv"""
import json, os, time, urllib.request, datetime as dt

OUT = os.environ.get("OUT_DIR", "feed/data/research")
TICKERS = """NVDA AMD AVGO TSM MU ARM MRVL ANET VRT SMCI ALAB CRDO WDC STX INTC QCOM LRCX AMAT KLAC
PLTR CRWD NET SNOW DDOG MDB ZS PANW NOW SHOP APP TTD RDDT DUOL AXON NBIS CRWV ORCL
COIN MSTR HOOD SOFI AFRM UPST NU MELI SE
TSLA META AMZN GOOGL MSFT AAPL NFLX UBER ABNB DASH RBLX DKNG CVNA CAVA ONON HIMS CELH ELF
RKLB ASTS LUNR SPCX IONQ RGTI QBTS OKLO SMR CEG VST NRG GEV CCJ LEU EOSE PLUG FSLR
IREN CIFR WULF CORZ BABA PDD JD LLY NVO VKTX MRNA SPY QQQ COST BRK-B GLD""".split()


def get(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5y&interval=1d"
    for a in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=20).read())["chart"]["result"][0]
        except Exception:
            time.sleep(1 + a)
    return None


os.makedirs(f"{OUT}/us_1d", exist_ok=True)
for s in TICKERS:
    r = get(s)
    if not r or "timestamp" not in r:
        print(s, "ERR"); continue
    q = r["indicators"]["quote"][0]
    n = 0
    with open(f"{OUT}/us_1d/{s}.csv", "w") as f:
        f.write("date,open,high,low,close,volume\n")
        for t, o, h, l, c, v in zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"]):
            if None in (o, h, l, c):
                continue
            f.write(f"{dt.datetime.fromtimestamp(t, dt.timezone.utc).date()},{o:.4f},{h:.4f},{l:.4f},{c:.4f},{v or 0}\n"); n += 1
    print(s, n)
    time.sleep(0.2)
