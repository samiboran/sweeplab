"""Larry Williams Ultimate Oscillator divergence test (daily).
Bull: UO pivot low A < 30; later pivot low B with price low lower but UO higher; signal when UO
crosses above the max UO between A and B (within 15 bars of B). Bear = mirror (A > 70).
Compared with 'naive' divergences (condition 1 only, signal at B confirmation) and with all days."""
import csv, glob, os, sys, statistics as st

def load(path):
    r = list(csv.DictReader(open(path)))
    return [(float(x["high"]), float(x["low"]), float(x["close"])) for x in r if x["close"] not in ("", "null")]

def uo(b):
    bp, tr = [0.0], [1e-12]
    for i in range(1, len(b)):
        h, l, c = b[i]; pc = b[i-1][2]
        bp.append(c - min(l, pc)); tr.append(max(h, pc) - min(l, pc) or 1e-12)
    out = [None]*len(b)
    for i in range(28, len(b)):
        a = lambda n: sum(bp[i-n+1:i+1]) / sum(tr[i-n+1:i+1])
        out[i] = 100 * (4*a(7) + 2*a(14) + a(28)) / 7
    return out

K = 3
def pivots(u, low):
    p = []
    for i in range(28+K, len(u)-K):
        w = u[i-K:i+K+1]
        if (low and u[i] == min(w)) or (not low and u[i] == max(w)):
            p.append(i)
    return p

def signals(b, u, bull):
    lows = [x[1] for x in b]; highs = [x[0] for x in b]
    piv = pivots(u, bull); full, naive = [], []
    for j in range(1, len(piv)):
        bI = piv[j]
        for aI in reversed(piv[:j]):
            if bI - aI < 5: continue
            if bI - aI > 60: break
            pa = min(lows[aI-K:aI+K+1]) if bull else max(highs[aI-K:aI+K+1])
            pb = min(lows[bI-K:bI+K+1]) if bull else max(highs[bI-K:bI+K+1])
            div = (pb < pa and u[bI] > u[aI]) if bull else (pb > pa and u[bI] < u[aI])
            if not div: continue
            naive.append(bI + K)
            if (u[aI] < 30) if bull else (u[aI] > 70):
                mid = max(u[aI:bI+1]) if bull else min(u[aI:bI+1])
                for t in range(bI + K, min(bI + 15, len(u))):
                    if (u[t] > mid) if bull else (u[t] < mid):
                        full.append(t); break
            break
    return sorted(set(full)), sorted(set(naive))

def fwd(b, idx, n, bull):
    out = []
    for t in idx:
        if t + n < len(b):
            r = (b[t+n][2] / b[t][2] - 1) * 100
            out.append(r if bull else -r)
    return out

def summ(x):
    if not x: return "  n=0"
    return f"n={len(x):4d}  ort {st.mean(x):+6.2f}%  medyan {st.median(x):+6.2f}%  kazanan {sum(1 for v in x if v>0)/len(x)*100:4.0f}%"

for name, pat in [("ABD hisseleri", sys.argv[1]), ("Kripto (30 coin)", sys.argv[2])]:
    files = [f for f in glob.glob(pat) if not os.path.basename(f).startswith(("SPY", "QQQ"))]
    print(f"\n######## {name}: {len(files)} sembol ########")
    for bull in (True, False):
        R = {k: {n: [] for n in (5, 10, 20)} for k in ("full", "naive", "all")}
        for f in files:
            b = load(f)
            if len(b) < 200: continue
            u = uo(b); full, naive = signals(b, u, bull)
            alld = list(range(40, len(b)))
            for k, idx in (("full", full), ("naive", naive), ("all", alld)):
                for n in (5, 10, 20):
                    R[k][n] += fwd(b, idx, n, bull)
        print(f"\n== {'ALIM (bull)' if bull else 'SATIM (bear)'} diverjansı — yön lehine getiri ==")
        for n in (5, 10, 20):
            print(f" {n:2d} gün | 3 koşul: {summ(R['full'][n])}")
            print(f"        | sadece diverjans: {summ(R['naive'][n])}")
            print(f"        | tüm günler: {summ(R['all'][n])}")
