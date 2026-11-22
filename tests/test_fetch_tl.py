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
    assert ids == ["gram_altin", "gram_gumus", "dolar", "bist100_usd", "btc", "eth"]
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


def test_one_year_ago_value_and_change():
    s = {}
    d = dt.date(2025, 1, 1)
    while d <= dt.date(2026, 11, 20):
        s[d.isoformat()] = 100.0 if d <= dt.date(2025, 11, 20) else 150.0
        d += dt.timedelta(days=1)
    st = tl.stats(s)
    assert st["date_1y"] == "2025-11-20" and st["val_1y"] == 100.0 and st["chg_1y"] == 50.0
    cs = tl.chart_series(s)
    assert cs[0][0] <= "2025-11-20" and len(cs) == tl.SERIES_DAYS + 1


def test_no_one_year_value_when_history_is_short():
    st = tl.stats(series("2026-06-01", 100, lambda i: 1.0))
    assert st["chg_1y"] is None and st["date_1y"] is None


def test_band_alternates():
    import datetime as _dt
    days = [(_dt.date(2026, 1, 1) + _dt.timedelta(days=i)).isoformat() for i in range(30)]
    usd = {d: 40.0 for d in days}
    gold = {d: 3000.0 + i for i, d in enumerate(days)}
    brent = {d: 70.0 for d in days[:-1]}
    brent[days[-1]] = 63.0
    d = tl.derive({"USDTRY": usd, "GOLD_USD": gold, "BRENT_USD": brent}, days[-1])
    b = d["band"]
    assert b["ons_altin"]["last"] == 3029.0 and b["ons_altin"]["unit"] == "$"
    assert b["brent"]["chg_1g"] == -10.0
    assert "wti" not in b and "ons_gumus" not in b      # missing inputs are simply left out
    assert all(set(v) <= {"label", "unit", "asof", "last", "chg_1g", "stale"} for v in b.values())


def test_compare_series_rebases_indices_and_keeps_prices():
    import datetime as _dt
    days = [(_dt.date(2026, 1, 1) + _dt.timedelta(days=i)).isoformat() for i in range(60)]
    usd = {d: 40.0 + i * 0.1 for i, d in enumerate(days)}
    gold = {d: 3000.0 for d in days}
    xu = {d: 10000.0 + i for i, d in enumerate(days)}
    c = tl.compare_series({"USDTRY": usd, "GOLD_USD": gold, "XU100": xu}, "2026-03-01")
    by = {a["id"]: a for a in c["assets"]}
    assert by["ons_altin"]["kind"] == "fiyat" and by["ons_altin"]["v"][0] == 3000.0
    assert by["bist100_tl"]["kind"] == "endeks" and by["bist100_tl"]["v"][0] == 100.0   # no index level published
    assert all(v is None or v < 1000 for v in by["bist100_tl"]["v"])
    assert "brent" not in by                                     # missing input -> left out
    assert len(c["dates"]) == len(by["dolar"]["v"])
    assert c["dates"][-1] < "2026-03-01"                          # today's (incomplete) bar excluded
