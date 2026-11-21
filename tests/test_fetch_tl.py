"""Tests for tools/fetch_tl.py derived values (no network) and the JS calculator."""
import datetime as dt, json, os, shutil, subprocess, sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import fetch_tl as tl  # noqa: E402


def series(start, n, f):
    d0 = dt.date.fromisoformat(start)
    out, i, d = {}, 0, d0
    while len(out) < n:
        if d.weekday() < 5:
            out[d.isoformat()] = f(i)
            i += 1
        d += dt.timedelta(days=1)
    return out


def test_gram_gold_formula():
    usd = {"2026-11-20": 50.0}
    gold = {"2026-11-20": 3110.35}
    g = tl.combine(gold, usd, lambda a, u: a * u / tl.OZ_GRAM)
    assert g["2026-11-20"] == pytest.approx(5000.0)


def test_combine_forward_fills_missing_rate():
    g = tl.combine({"2026-01-01": 1.0, "2026-01-02": 2.0}, {"2025-12-31": 10.0}, lambda a, u: a * u)
    assert g == {"2026-01-01": 10.0, "2026-01-02": 20.0}


def test_stats_changes_and_ma():
    s = series("2024-06-03", 260, lambda i: 100.0 + i)
    st = tl.stats(s)
    last = 100.0 + 259
    assert st["last"] == last
    assert st["chg_1g"] == pytest.approx(round((last / (last - 1) - 1) * 100, 2))
    ma = sum(100.0 + i for i in range(60, 260)) / 200
    assert st["vs_ma200"] == pytest.approx(round((last / ma - 1) * 100, 2))
    assert st["chg_ytd"] is not None and st["chg_7g"] > 0 and st["chg_30g"] > st["chg_7g"]


def test_derive_publishes_derived_only():
    usd = series("2024-01-01", 300, lambda i: 30 + i * 0.05)
    gold = series("2024-01-01", 300, lambda i: 2000 + i)
    silver = series("2024-01-01", 300, lambda i: 25 + i * 0.01)
    xu = series("2024-01-01", 300, lambda i: 9000 + i)
    last = max(usd)
    d = tl.derive({"USDTRY": usd, "GOLD_USD": gold, "SILVER_USD": silver, "XU100": xu}, last,
                  {"btc": {"asof": last, "usd": 60000.0}})
    ids = [a["id"] for a in d["assets"]]
    assert ids == ["gram_altin", "gram_gumus", "dolar", "bist100_usd"]
    bist = d["assets"][3]
    assert bist["last"] is None and bist["series"][0][1] == 100.0          # rebased, no index levels
    assert len(d["assets"][0]["series"]) <= tl.SERIES_DAYS
    assert d["prices"]["btc_usd"] == 60000.0 and d["status"] == "ok"
    blob = json.dumps(d)
    assert "GOLD_USD" not in blob and "SILVER_USD" not in blob and "XU100" not in blob


def test_stale_flag():
    usd = series("2024-01-01", 250, lambda i: 30.0)
    gold = series("2024-01-01", 250, lambda i: 2000.0)
    d = tl.derive({"USDTRY": usd, "GOLD_USD": gold}, "2030-01-01")
    assert d["status"] == "güncellenmedi" and d["assets"][1]["status"] == "veri yok"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_calculator_js():
    here = os.path.dirname(__file__)
    out = subprocess.run(["node", os.path.join(here, "hesapla_test.js")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr


def test_is_daily_rejects_monthly_bars():
    monthly = {f"{y}-{m:02d}-01": 1.0 for y in range(2020, 2027) for m in range(1, 13)}
    assert not tl.is_daily(monthly)
    assert tl.is_daily(series("2024-01-01", 600, lambda i: 1.0))


def test_update_raw_rebuilds_monthly_store(tmp_path, monkeypatch):
    monkeypatch.setattr(tl, "RAW_DIR", str(tmp_path))
    monthly = {f"{y}-{m:02d}-01": 1.0 for y in range(2010, 2027) for m in range(1, 13)}
    for n in tl.SYMBOLS:
        tl.write_csv(str(tmp_path / f"{n}.csv"), monthly)
    daily = series("2020-01-01", 1500, lambda i: 2.0)
    calls = []
    monkeypatch.setattr(tl, "yahoo", lambda sym, start=None, rng="1y": calls.append(start) or dict(daily))
    data = tl.update_raw()
    assert all(c == tl.BACKFILL_START for c in calls)
    assert all(tl.is_daily(v) and len(v) == 1500 for v in data.values())
    assert tl.read_csv(str(tmp_path / "USDTRY.csv")) == daily
