"""Daily BTC/ETH derivatives snapshot: open interest, funding, long/short ratio, liquidations.
Tries several public exchange APIs; records what each one returned (or its error)."""
import json, urllib.request, datetime, os

def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"ok": True, "status": r.status, "data": json.loads(r.read())}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

out = {"fetched_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"), "sources": {}}
S = out["sources"]
for coin in ["BTC", "ETH"]:
    sym = coin + "USDT"
    S[f"binance_{coin}"] = {
        "oi_hist_1h": get(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={sym}&period=1h&limit=48"),
        "funding": get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&limit=9"),
        "ls_ratio_1h": get(f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={sym}&period=1h&limit=48"),
        "taker_ratio_1h": get(f"https://fapi.binance.com/futures/data/takerlongshortRatio?symbol={sym}&period=1h&limit=48"),
    }
    S[f"bybit_{coin}"] = {
        "oi_1h": get(f"https://api.bybit.com/v5/market/open-interest?category=linear&symbol={sym}&intervalTime=1h&limit=48"),
        "funding": get(f"https://api.bybit.com/v5/market/funding/history?category=linear&symbol={sym}&limit=9"),
        "ls_ratio_1h": get(f"https://api.bybit.com/v5/market/account-ratio?category=linear&symbol={sym}&period=1h&limit=48"),
    }
    S[f"okx_{coin}"] = {
        "oi_vol_1h": get(f"https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume?ccy={coin}&period=1H"),
        # [ts, oi(contracts), oiCcy, oiUsd] for the USDT perp, hourly: coin-denominated OI
        "oi_hist_1h": get(f"https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history?instId={coin}-USDT-SWAP&period=1H&limit=48"),
        "ls_ratio_1h": get(f"https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy={coin}&period=1H"),
        "funding": get(f"https://www.okx.com/api/v5/public/funding-rate-history?instId={coin}-USDT-SWAP&limit=9"),
        "liquidations": get(f"https://www.okx.com/api/v5/public/liquidation-orders?instType=SWAP&uly={coin}-USDT&state=filled&limit=100"),
    }
hl = get("https://api.hyperliquid.xyz/info", data=json.dumps({"type": "metaAndAssetCtxs"}).encode())
if hl["ok"]:
    try:
        meta, ctxs = hl["data"]
        hl["data"] = {u["name"]: c for u, c in zip(meta["universe"], ctxs) if u["name"] in ("BTC", "ETH")}
    except Exception as e:
        hl = {"ok": False, "error": "parse " + str(e)}
S["hyperliquid"] = hl

OUT_DIR = os.environ.get("OUT_DIR", "data/derivs")
os.makedirs(OUT_DIR, exist_ok=True)
day = out["fetched_utc"][:13].replace("T", "_")
for p in (f"{OUT_DIR}/{day}.json", f"{OUT_DIR}/latest.json"):
    json.dump(out, open(p, "w"), indent=1)
for k, v in S.items():
    items = v.items() if "ok" not in v else [("all", v)]
    print(k, {n: ("OK" if x["ok"] else x["error"][:60]) for n, x in items})
