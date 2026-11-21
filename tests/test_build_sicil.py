"""Tests for tools/build_sicil.py (track record check)."""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_sicil as bsc  # noqa: E402
import build_site as bs  # noqa: E402


def _days(start, n):
    d0 = dt.date.fromisoformat(start)
    return [(d0 + dt.timedelta(days=k)).isoformat() for k in range(n)]


def test_signals_first_day_of_kirmizi_runs():
    lv = ["SARI", "KIRMIZI", "KIRMIZI", "SARI", "KIRMIZI"]
    hist = [{"date": d, "level": l} for d, l in zip(_days("2026-10-01", 5), lv)]
    assert [h["date"] for h in bsc.signals(hist)] == ["2026-10-02", "2026-10-05"]


def test_evaluate_confirm_false_alarm_pending():
    days = _days("2026-10-01", 30)
    flat = {d: 100.0 for d in days}
    assert bsc.evaluate("2026-10-01", flat, days[-1])["result"] == "yanlış alarm"
    assert bsc.evaluate("2026-10-20", flat, days[-1])["result"] == "bekliyor"
    drop = dict(flat)
    drop["2026-10-08"] = 94.9
    ev = bsc.evaluate("2026-10-01", drop, days[-1])
    assert ev["result"] == "teyit edildi" and ev["days_to_confirm"] == 7
    # exactly -5% counts; -4.9% does not
    edge = dict(flat, **{"2026-10-08": 95.0})
    assert bsc.evaluate("2026-10-01", edge, days[-1])["result"] == "teyit edildi"
    edge = dict(flat, **{"2026-10-08": 95.1})
    assert bsc.evaluate("2026-10-01", edge, days[-1])["result"] == "yanlış alarm"
    # drop after the 20-day window does not count
    late = dict(flat, **{"2026-10-25": 80.0})
    assert bsc.evaluate("2026-10-01", late, days[-1])["result"] == "yanlış alarm"


def test_misses_only_when_never_kirmizi():
    days = _days("2026-10-01", 30)
    ndx = {d: 100.0 for d in days}
    ndx["2026-10-15"] = 89.0
    hist = [{"date": d, "level": "SARI", "mode": "retro"} for d in days]
    m = bsc.misses(hist, ndx)
    assert [x["date"] for x in m] == ["2026-10-15"]
    hist[5]["level"] = "KIRMIZI"
    assert bsc.misses(hist, ndx) == []


def test_build_is_append_only(tmp_path):
    days = _days("2026-10-01", 40)
    rows = []
    for k, d in enumerate(days):
        v = 100.0 - (6.0 if k >= 10 else 0.0)
        r = {"date": d, "regime": {}, "risk": {"ndx": v}, "macro": {}}
        rows.append(r)
    nb = tmp_path / "nb.json"
    nb.write_text(json.dumps({"rows": rows}))
    site = tmp_path / "site"
    site.mkdir()
    hist = [{"date": d, "rules_version": "v1", "mode": "retro", "raw_score": 5, "raw_level": "KIRMIZI",
             "level": "KIRMIZI" if d == "2026-10-05" else "SARI", "level_held": 0} for d in days]
    bs.append_history(str(site / "history.csv"), [{k: h.get(k, "") for k in bs.HISTORY_FIELDS} for h in hist])
    orig = bs.settled_rows
    bs.settled_rows = lambda r: r          # synthetic rows carry no as-of dates
    try:
        bsc.build(str(site), str(nb))
        d = json.loads((site / "sicil.json").read_text())
        e = [x for x in d["entries"] if x["kind"] == "sinyal"]
        assert e[0]["date"] == "2026-10-05" and e[0]["result"] == "teyit edildi"
        assert d["source"] == "Piyasa Hava Durumu" and d["rules_version"] == "v1"
        assert "ndx" not in json.dumps(d).lower().replace("nasdaq", "")
        # a later rebuild with different data never rewrites a final result
        for r in rows:
            r["risk"]["ndx"] = 100.0
        nb.write_text(json.dumps({"rows": rows}))
        bsc.build(str(site), str(nb))
        d2 = json.loads((site / "sicil.json").read_text())
        assert [x for x in d2["entries"] if x["kind"] == "sinyal"][0]["result"] == "teyit edildi"
    finally:
        bs.settled_rows = orig
