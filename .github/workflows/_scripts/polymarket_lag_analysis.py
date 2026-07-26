"""
Polymarket 'temporal arbitrage' hipotezi: BTC/USDT gerceklesen fiyat hareketi ile
Polymarket 5dk Up/Down piyasalarinin implied-probability hareketi arasinda
sistematik bir gecikme (lag) var mi?

Veri:
  - Polymarket ticks/markets: kachoio/polymarket-5-minute-crypto-up-down-markets (HF)
  - BTC fiyati: Binance data.binance.vision bulk 1s klines (BTCUSDT)

Metodoloji:
  - Havuzlanmis (pooled) cross-correlation: tum saniyeler tek bir zaman ekseninde
    birlestirilir, her lag icin Pearson korelasyonu hesaplanir (per-market degil,
    tum veri havuzunda -- cok daha yuksek istatistiksel guc).
  - d_mid_up her piyasanin ILK tick'inde NaN (groupby(condition_id).diff()) --
    piyasalar arasi sahte sureklilik onlenir.
  - Rastgele kontrol: ret_btc serisi rastgele buyuk ofsetlerle dairesel kaydirilir
    (gercek hizalama bozulur, kendi otokorelasyon yapisi korunur) -- N tekrar,
    null band (ortalama +- 2*std).
  - Walk-forward: piyasalar market_start medyanina gore ikiye bolunur, lag egrisi
    ayri ayri hesaplanir.
  - Spread: au-bu dogrudan olculur, peak lag'teki yakalanabilir hareketle
    karsilastirilir.
"""
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA_DIR = Path("data")
OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

LAGS = list(range(-30, 31))
N_CONTROL_SHIFTS = 20
RNG = np.random.default_rng(42)


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# 1) BTC price series from Binance 1s klines
# ---------------------------------------------------------------------------
def load_btc_price():
    kline_cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ]
    frames = []
    for f in sorted(DATA_DIR.glob("BTCUSDT-1s-*.zip")):
        log(f"reading {f}")
        with zipfile.ZipFile(f) as zf:
            inner = zf.namelist()[0]
            with zf.open(inner) as fh:
                first = fh.readline()
        skiprows = 1 if first.split(b",")[0].strip().isdigit() is False else 0
        df = pd.read_csv(
            f, compression="zip", names=kline_cols, header=None,
            skiprows=skiprows, usecols=["open_time", "close"],
            dtype={"open_time": "int64", "close": "float64"},
        )
        frames.append(df)
    btc = pd.concat(frames, ignore_index=True)
    btc["t"] = (btc["open_time"] // 1000).astype("int64")
    btc = btc.drop_duplicates("t").sort_values("t")
    price = pd.Series(btc["close"].values, index=btc["t"].values, name="price")
    log(f"btc price series: {len(price)} seconds, {price.index.min()} .. {price.index.max()}")
    ret = np.log(price / price.shift(1))
    ret.name = "ret_btc"
    return ret


# ---------------------------------------------------------------------------
# 2) Polymarket ticks + markets
# ---------------------------------------------------------------------------
def load_polymarket():
    from datasets import load_dataset

    log("loading ticks/btc ...")
    ticks = load_dataset(
        "kachoio/polymarket-5-minute-crypto-up-down-markets", "ticks", split="btc"
    ).to_pandas()
    log(f"ticks: {len(ticks)} rows")

    log("loading markets/btc ...")
    markets = load_dataset(
        "kachoio/polymarket-5-minute-crypto-up-down-markets", "markets", split="btc"
    ).to_pandas()
    log(f"markets: {len(markets)} rows")

    ticks["mid_up"] = (ticks["bu"] + ticks["au"]) / 2.0
    ticks["spread"] = ticks["au"] - ticks["bu"]
    ticks = ticks.sort_values(["condition_id", "t"])
    ticks["d_mid_up"] = ticks.groupby("condition_id")["mid_up"].diff()

    m = markets[["condition_id", "market_start"]].copy()
    epoch0 = pd.Timestamp("1970-01-01", tz="UTC")
    m["market_start_epoch"] = (m["market_start"] - epoch0) // pd.Timedelta("1s")
    ticks = ticks.merge(m[["condition_id", "market_start_epoch"]], on="condition_id", how="left")
    return ticks


# ---------------------------------------------------------------------------
# 3) pooled cross-correlation vs lag
# ---------------------------------------------------------------------------
def lag_curve(ret_btc, ticks_subset, lags=LAGS):
    df = ticks_subset.set_index("t")[["d_mid_up"]].join(ret_btc, how="inner")
    df = df.dropna(subset=["ret_btc"])
    rows = []
    for L in lags:
        shifted = df["d_mid_up"].shift(-L)
        valid = shifted.notna()
        n = int(valid.sum())
        if n < 100:
            rows.append((L, np.nan, np.nan, n))
            continue
        x = df["ret_btc"][valid].values
        y = shifted[valid].values
        r, p = stats.pearsonr(x, y)
        rows.append((L, r, p, n))
    return pd.DataFrame(rows, columns=["lag", "corr", "pvalue", "n"])


def control_band(ret_btc, ticks_subset, lags=LAGS, n_shifts=N_CONTROL_SHIFTS):
    total_span = int(ret_btc.index.max() - ret_btc.index.min())
    curves = []
    for i in range(n_shifts):
        offset = int(RNG.integers(3700, max(3701, total_span - 3700)))
        shifted_index = ret_btc.index + offset
        shifted_ret = pd.Series(ret_btc.values, index=shifted_index, name="ret_btc")
        c = lag_curve(shifted_ret, ticks_subset, lags=lags)
        curves.append(c.set_index("lag")["corr"])
        log(f"  control shift {i+1}/{n_shifts} (offset={offset}s) done")
    mat = pd.concat(curves, axis=1)
    return pd.DataFrame({
        "lag": mat.index,
        "control_mean": mat.mean(axis=1).values,
        "control_std": mat.std(axis=1).values,
    })


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ret_btc = load_btc_price()
    ticks = load_polymarket()

    real = lag_curve(ret_btc, ticks)
    log("\n=== full-period real lag curve ===")
    log(real.to_string(index=False))
    peak = real.loc[real["corr"].abs().idxmax()]
    log(f"\npeak lag = {int(peak['lag'])}s, corr={peak['corr']:.4f}, p={peak['pvalue']:.2e}, n={int(peak['n'])}")

    log("\ncomputing random-control null band...")
    ctrl = control_band(ret_btc, ticks)

    full = real.merge(ctrl, on="lag")
    full.to_csv(OUT_DIR / "lag_curve_full.csv", index=False)

    # --- walk-forward split ---
    med = ticks["market_start_epoch"].median()
    first_half = ticks[ticks["market_start_epoch"] < med]
    second_half = ticks[ticks["market_start_epoch"] >= med]
    log(f"\nwalk-forward split at epoch {med}: first_half n={len(first_half)}, second_half n={len(second_half)}")

    real_h1 = lag_curve(ret_btc, first_half)
    real_h2 = lag_curve(ret_btc, second_half)
    real_h1.to_csv(OUT_DIR / "lag_curve_first_half.csv", index=False)
    real_h2.to_csv(OUT_DIR / "lag_curve_second_half.csv", index=False)

    peak_h1 = real_h1.loc[real_h1["corr"].abs().idxmax()]
    peak_h2 = real_h2.loc[real_h2["corr"].abs().idxmax()]
    log(f"first half peak lag={int(peak_h1['lag'])}s corr={peak_h1['corr']:.4f}")
    log(f"second half peak lag={int(peak_h2['lag'])}s corr={peak_h2['corr']:.4f}")

    # --- spread cost check ---
    mean_spread = float(ticks["spread"].mean())
    q90 = ret_btc.abs().quantile(0.9)
    big_moves_t = set(ret_btc[ret_btc.abs() >= q90].index)
    peak_L = int(peak["lag"])
    df_join = ticks.set_index("t")[["d_mid_up"]].join(ret_btc, how="inner").dropna()
    df_join["is_big_move"] = df_join.index.isin(big_moves_t)
    shifted_for_peak = ticks.set_index("t")["d_mid_up"].shift(-peak_L)
    capturable = shifted_for_peak.reindex(list(big_moves_t)).abs().mean()

    summary = {
        "n_ticks": int(len(ticks)),
        "n_markets": int(ticks["condition_id"].nunique()),
        "date_range": [str(ticks["market_start_epoch"].min()), str(ticks["market_start_epoch"].max())],
        "peak_lag_seconds": int(peak["lag"]),
        "peak_corr": float(peak["corr"]),
        "peak_pvalue": float(peak["pvalue"]),
        "peak_n": int(peak["n"]),
        "control_mean_at_peak_lag": float(ctrl.set_index("lag").loc[peak_L, "control_mean"]),
        "control_std_at_peak_lag": float(ctrl.set_index("lag").loc[peak_L, "control_std"]),
        "walk_forward": {
            "first_half_peak_lag": int(peak_h1["lag"]),
            "first_half_peak_corr": float(peak_h1["corr"]),
            "second_half_peak_lag": int(peak_h2["lag"]),
            "second_half_peak_corr": float(peak_h2["corr"]),
        },
        "spread": {
            "mean_spread": mean_spread,
            "mean_abs_capturable_move_at_peak_lag_top_decile_btc_moves": float(capturable),
            "spread_exceeds_capturable_move": bool(mean_spread > capturable),
        },
    }
    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    log("\n=== SUMMARY ===")
    log(json.dumps(summary, indent=2))

    # --- plots ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(full["lag"], full["corr"], label="gerçek (full period)", color="#1f77b4")
    ax.fill_between(
        full["lag"],
        full["control_mean"] - 2 * full["control_std"],
        full["control_mean"] + 2 * full["control_std"],
        color="gray", alpha=0.3, label="rastgele kontrol (±2σ)",
    )
    ax.axvline(0, color="black", lw=0.5)
    ax.set_xlabel("lag (saniye, + = Polymarket BTC'den sonra tepki veriyor)")
    ax.set_ylabel("Pearson korelasyon")
    ax.set_title("BTC hareketi vs Polymarket mid_up hareketi: lag korelasyon eğrisi")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "lag_curve.png", dpi=140)

    fig2, ax2 = plt.subplots(figsize=(9, 5))
    ax2.plot(real_h1["lag"], real_h1["corr"], label="ilk yarı (Mart-Nisan)")
    ax2.plot(real_h2["lag"], real_h2["corr"], label="ikinci yarı (Nisan-Mayıs)")
    ax2.axvline(0, color="black", lw=0.5)
    ax2.set_xlabel("lag (saniye)")
    ax2.set_ylabel("Pearson korelasyon")
    ax2.set_title("Walk-forward: lag korelasyon eğrisi, ilk yarı vs ikinci yarı")
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig(OUT_DIR / "lag_curve_walkforward.png", dpi=140)

    log("\ndone.")


if __name__ == "__main__":
    main()
