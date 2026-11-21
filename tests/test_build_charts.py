"""Tests for tools/build_charts.py (S5 chart data, derived only)."""
import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_charts as bc  # noqa: E402

DAY = 86400000


def raw(tmp_path, n=260):
    t0 = 1735689600000  # 2025-01-01
    candles = [[str(t0 + i * DAY), "1", "2", "0.5", str(100 + i), "9", "9", "9", "1"] for i in range(n)]
    candles[-1][8] = "0"  # still forming: must be skipped
    p = tmp_path / "okx.json"
    p.write_text(json.dumps({"BTC": {"candles": {"ok": True, "data": candles}},
                             "ETH": {"candles": {"ok": True, "data": candles}}}))
    return str(p)


def test_closes_skip_unconfirmed(tmp_path):
    c = bc.okx_closes(raw(tmp_path), "btc")
    assert len(c) == 259 and max(c) == "2025-09-16"


def test_moving_averages(tmp_path):
    s = bc.with_ma({f"2025-01-{i + 1:02d}": float(i) for i in range(30)} |
                   {f"2025-02-{i + 1:02d}": float(30 + i) for i in range(28)}, days=10)
    assert len(s) == 10 and s[-1][2] == round(sum(range(8, 58)) / 50, 2) and s[-1][3] is None


def test_build_derived_only(tmp_path, monkeypatch):
    monkeypatch.setattr(bc, "RESEARCH", str(tmp_path / "none"))
    h = tmp_path / "history.csv"
    h.write_text("date,rules_version,mode,raw_score,raw_level,level,level_held\n"
                 "2026-11-20,v1,retro,7,KIRMIZI,KIRMIZI,0\n2026-11-21,v1,live,6,KIRMIZI,KIRMIZI,0\n")
    rec = bc.build(raw(tmp_path), str(h), now="2026-11-22T06:00:00Z")
    assert rec["source"] and rec["attribution"] and rec["site_url"]
    assert rec["macro"][-1] == ["2026-11-21", 6, "KIRMIZI", "live", "v1"]
    assert rec["version_boundaries"] == [{"date": "2026-11-20", "rules_version": "v1"}]
    row = rec["crypto"]["btc"]["series"][-1]
    assert len(row) == 4 and row[3] is not None          # date, close, ma50, ma200 only
    assert "oi" not in json.dumps(rec["crypto"]) and "funding" not in json.dumps(rec)
