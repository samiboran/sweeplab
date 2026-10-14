"""Momentum pullback (Qullamaggie/Martin Luk style) on 30 large-cap coins, daily bars.
Rules fixed BEFORE running:
 setup day t: ret21>=30% or ret63>=30%; EMA9>EMA21>EMA50; EMA21 rising vs 5d ago; ADR20>=5%;
              pullback/reclaim: low<=EMA9 and close>=EMA9 (touched support, closed back above)
 entry: next open. stop: setup-day low*0.995; skip if stop dist <1% or >8%.
 exits: A) initial stop; at +3R sell 20%; after 3R exit rest on daily close<EMA9 (next open); time stop 40d
        B) same but trail on close<EMA21
 costs: 0.1%/side + 0.03%/day funding. One open trade per coin.
 baseline: same filters minus the pullback condition, random day, same exits (300 reps).
 split: train 2020-2023, test 2024-2026.
"""
import glob, os, numpy as np, pandas as pd, sys
D = os.path.dirname(os.path.abspath(__file__)) + '/../data/research/us_1d/'
FEE, FUND = 0.0005, 0.0
data = {}
for f in glob.glob(D + '*.csv'):
    c = os.path.basename(f)[:-4]
    if c in ('SPY','QQQ','GLD'): continue
    d = pd.read_csv(f); d['dt'] = pd.to_datetime(d.date); d = d.set_index('dt')
    for n in (9, 21, 50): d[f'e{n}'] = d.close.ewm(span=n, adjust=False).mean()
    d['r21'] = d.close / d.close.shift(21) - 1; d['r63'] = d.close / d.close.shift(63) - 1
    d['adr'] = (d.high / d.low - 1).rolling(20).mean()
    d['base'] = (((d.r21 >= .3) | (d.r63 >= .3)) & (d.e9 > d.e21) & (d.e21 > d.e50) & (d.e21 > d.e21.shift(5)) & (d.adr >= .05))
    d['sig'] = d.base & (d.low <= d.e9) & (d.close >= d.e9)
    data[c] = d.iloc[60:]

def run_trade(d, k, mode):
    """k = setup index. returns (R multiple net, days, entry date) or None"""
    if k + 1 >= len(d): return None
    e = d.open.iloc[k + 1]; stop = d.low.iloc[k] * 0.995
    dist = (e - stop) / e
    if dist < 0.01 or dist > 0.08: return None
    trail = 'e9' if mode == 'A' else 'e21'
    tgt = e * (1 + 3 * dist); took = False; pnl = 0.0; frac = 1.0
    for j in range(k + 1, min(k + 41, len(d))):
        lo, hi, cl = d.low.iloc[j], d.high.iloc[j], d.close.iloc[j]
        if not took and lo <= stop:
            pnl += frac * (stop / e - 1); frac = 0; break
        if not took and hi >= tgt:
            pnl += 0.2 * (tgt / e - 1); frac = 0.8; took = True
        if took and cl < d[trail].iloc[j]:
            px = d.open.iloc[j + 1] if j + 1 < len(d) else cl
            pnl += frac * (px / e - 1); frac = 0; break
    else:
        pass
    if frac > 0:
        jj = min(k + 40, len(d) - 1); pnl += frac * (d.close.iloc[jj] / e - 1); j = jj
    days = j - k
    net = pnl - 2 * FEE - FUND * days
    return net / dist, net, days, d.index[k + 1]

def trades(mode, picker):
    out = []
    for c, d in data.items():
        busy = -1
        for k in picker(d):
            if k <= busy: continue
            t = run_trade(d, k, mode)
            if t: out.append((c,) + t); busy = k + t[2]
    return pd.DataFrame(out, columns=['coin', 'R', 'ret', 'days', 'date'])

sig_pick = lambda d: np.where(d.sig.values)[0]
def stats(t, lab):
    if t.empty: print(lab, 'n=0'); return
    w = t.R > 0
    print(f"{lab:22} n={len(t):4} kazanma %{w.mean()*100:4.0f}  ortR {t.R.mean():+.2f}  medR {t.R.median():+.2f}  "
          f"kazanan ort {t.R[w].mean():+.2f}R  kaybeden ort {t.R[~w].mean():+.2f}R  >=3R %{(t.R>=3).mean()*100:.0f}  topR {t.R.sum():+.0f}")
rng = np.random.default_rng(7)
for mode in ('A', 'B'):
    T = trades(mode, sig_pick)
    for lab, a, b in (('eğitim 2021–23', '2021', '2023'), ('test 2024–26', '2024', '2026')):
        tt = T[(T.date >= a) & (T.date <= b + '-12-31')]
        stats(tt, f"{mode} {lab}")
        # baseline
        means = []
        for _ in range(200):
            def rp(d, a=a, b=b):
                idx = np.where(d.base.values & (d.index >= a) & (d.index <= b + '-12-31'))[0]
                if len(idx) == 0: return []
                return np.sort(rng.choice(idx, size=min(len(idx), max(1, int(len(idx) * 0.25))), replace=False))
            bt = trades(mode, rp); means.append(bt.R.mean())
            if len(means) >= 30: break
        print(f"   rastgele (aynı filtre, geri çekilme şartı yok) ortR {np.mean(means):+.2f}  [aralık {np.percentile(means,5):+.2f}..{np.percentile(means,95):+.2f}]")
    T.to_csv(os.path.dirname(os.path.abspath(__file__)) + f'/us_trades_{mode}.csv', index=False)
