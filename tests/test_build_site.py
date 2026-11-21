"""Tests for tools/build_site.py (macro weather rules v1)."""
import copy
import csv
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_site as bs  # noqa: E402

# The two notebook rows the 2026-11-19 score depends on (20 rows apart), as on data-feed.
BASE_1030 = {"date": "2026-10-30",
             "regime": {"stables_7d_pct": -1.154589, "netliq_musd": 5745732.0, "real10y": 2.6, "dxy": 101.879997},
             "risk": {"hy_oas": 3.44, "vix": 19.42, "ndx": 25437.0},
             "macro": {"gold": 3898.899902, "wti": 104.120003}}
ROW_1119 = {"date": "2026-11-19",
            "regime": {"stables_7d_pct": -1.327557, "netliq_musd": 5824508.0, "real10y": 2.88, "dxy": 103.900002},
            "risk": {"hy_oas": 3.52, "vix": 28.44, "ndx": 23879.2},
            "macro": {"gold": 3685.5, "wti": 83.209999}}


def _rows_with(base, cur, n=20):
    rows = [copy.deepcopy(base)]
    d0 = dt.date.fromisoformat(base["date"])
    for k in range(1, n):
        f = copy.deepcopy(base)
        f["date"] = (d0 + dt.timedelta(days=k)).isoformat()
        rows.append(f)
    rows.append(copy.deepcopy(cur))
    return rows


def _asof(row, d):
    row["regime"].update(stables_asof=d, netliq_asof=d, real10y_asof=d, dxy_asof=d)
    row["risk"].update(hy_asof=d, vix_asof=d, ndx_asof=d)
    row["macro"].update(gold_asof=d, wti_asof=d)
    return row


def test_2026_11_19_scores_7_kirmizi():
    s = bs.score_row(_rows_with(BASE_1030, ROW_1119), 20)
    assert s["base_date"] == "2026-10-30"
    assert s["flags"] == {"L1": 1, "L2": 0, "L3": 1, "D1": 1, "K1": 0, "K2": 1, "K3": 1, "N1": 1, "P1": 1}
    assert s["raw_score"] == 7
    assert s["raw_level"] == "KIRMIZI"
    assert s["p1_label"] == "talep zayıflığı"


def test_levels():
    assert [bs.level_of(x) for x in range(10)] == ["YESIL"] * 3 + ["SARI"] * 2 + ["KIRMIZI"] * 5


def test_noise_filter():
    assert bs.publish_level(None, None, "SARI") == ("SARI", False)
    # one-day jump is held
    assert bs.publish_level("YESIL", "YESIL", "KIRMIZI") == ("YESIL", True)
    # second day in the same new level -> changes
    assert bs.publish_level("YESIL", "KIRMIZI", "KIRMIZI") == ("KIRMIZI", False)
    # yesterday SARI, today KIRMIZI -> not the same new level, held
    assert bs.publish_level("YESIL", "SARI", "KIRMIZI") == ("YESIL", True)


def test_oldest_row_when_fewer_than_20():
    rows = _rows_with(BASE_1030, ROW_1119, n=5)
    s = bs.score_row(rows, len(rows) - 1)
    assert s["base_date"] == "2026-10-30"


def test_missing_input_scores_zero_and_null():
    cur = copy.deepcopy(ROW_1119)
    cur["risk"]["vix"] = None
    s = bs.score_row(_rows_with(BASE_1030, cur), 20)
    assert s["flags"]["K2"] is None and s["raw_score"] == 6


def test_oil_inflation_label():
    cur = copy.deepcopy(ROW_1119)
    cur["macro"]["wti"] = BASE_1030["macro"]["wti"] * 1.11
    s = bs.score_row(_rows_with(BASE_1030, cur), 20)
    assert s["flags"]["P1"] == 1 and s["p1_label"] == "enflasyon dürtüsü"


def test_licensed_inputs_publish_direction_only():
    s = bs.score_row(_rows_with(BASE_1030, ROW_1119), 20)
    v = s["values"]
    assert v["hy_oas_20g_yon"] == "açıldı" and v["ndx_20g_yon"] == "düştü" and v["dxy_20g_yon"] == "yükseldi"
    blob = json.dumps(v)
    for raw in ("3.52", "23879", "103.9"):
        assert raw not in blob


def test_turkish_format():
    assert bs.tr_num(1234.56) == "1.234,6"
    assert bs.tr_num(-1.5) == "−1,5"
    assert bs.tr_date("2026-11-21") == "21 Kasım 2026"


def test_weekday_age_skips_weekends():
    assert bs.weekday_age("2026-11-20", "2026-11-23") == 1   # Fri -> Mon
    assert bs.weekday_age("2026-11-16", "2026-11-21") == 4   # Mon -> Sat


def test_build_backfill_append_and_history(tmp_path):
    rows = [_asof(r, "2026-11-19") for r in _rows_with(BASE_1030, ROW_1119)]
    nb = tmp_path / "nb.json"
    nb.write_text(json.dumps({"rows": rows}))
    site = tmp_path / "site"
    now = dt.datetime(2026, 11, 20, 6, 0, tzinfo=dt.timezone.utc)
    res = bs.build(str(nb), str(site), now)
    assert res["status"] == "ok" and res["appended"] == 21 and res["mode"] == "retro"
    today = json.loads((site / "today.json").read_text())
    for k in ("source", "site_url", "rules_version", "generated_at", "attribution", "mode", "status"):
        assert k in today
    # one-day jump from YEŞİL fillers: raw KIRMIZI, published level held
    assert today["status"] == "güncel" and today["raw_level"] == "KIRMIZI"
    assert today["level"] == "YESIL" and today["level_held"] is True and today["held_note"]
    assert len(list((site / "archive").iterdir())) == 21

    # next day: one new live row appended, older rows untouched
    nxt = _asof(copy.deepcopy(ROW_1119), "2026-11-23")
    nxt["date"] = "2026-11-23"
    rows.append(nxt)
    nb.write_text(json.dumps({"rows": rows[-21:]}))   # notebook window slides
    before = (site / "history.csv").read_text()
    res = bs.build(str(nb), str(site), dt.datetime(2026, 11, 24, 6, 0, tzinfo=dt.timezone.utc))
    assert res["appended"] == 1 and res["mode"] == "live"
    after = (site / "history.csv").read_text()
    assert after.startswith(before)
    hist = list(csv.DictReader(open(site / "history.csv")))
    assert len(hist) == 22 and hist[-1]["mode"] == "live"
    assert hist[-1]["level"] == "KIRMIZI"   # second day confirms the change

    # same data again: nothing appended
    res = bs.build(str(nb), str(site), dt.datetime(2026, 11, 24, 7, 0, tzinfo=dt.timezone.utc))
    assert res["status"] == "unchanged"


def test_stale_inputs_mark_guncellenmedi(tmp_path):
    rows = [_asof(r, "2026-11-19") for r in _rows_with(BASE_1030, ROW_1119)]
    nb = tmp_path / "nb.json"
    nb.write_text(json.dumps({"rows": rows}))
    site = tmp_path / "site"
    bs.build(str(nb), str(site), dt.datetime(2026, 11, 20, 6, 0, tzinfo=dt.timezone.utc))
    res = bs.build(str(nb), str(site), dt.datetime(2026, 11, 27, 6, 0, tzinfo=dt.timezone.utc))
    assert res["status"] == "stale"
    today = json.loads((site / "today.json").read_text())
    assert today["status"] == "güncellenmedi" and today["last_good_date"] == "2026-11-19"


def test_answers_have_no_action_words():
    s = bs.score_row(_rows_with(BASE_1030, ROW_1119), 20)
    rec = bs.build_record(s, "KIRMIZI", False, "retro", "2026-11-21T06:00:00Z", "2026-11-21", {})
    rec["answers"] = bs.answers(rec, None)
    text = json.dumps(rec, ensure_ascii=False).lower()
    for w in (" al ", " sat ", "fırsat", "ucuz", "hedef", "kaçırma", "🚀"):
        assert w not in text


def test_settled_skips_row_with_previous_day_us_data():
    rows = _rows_with(_asof(copy.deepcopy(BASE_1030), "2026-10-30"), _asof(copy.deepcopy(ROW_1119), "2026-11-19"))
    nxt = _asof(copy.deepcopy(ROW_1119), "2026-11-20")
    nxt["date"] = "2026-11-20"
    nxt["risk"]["vix_asof"] = "2026-11-19"          # FRED not out yet for 11-20
    assert bs.settled(rows, len(rows) - 1) and not bs.settled(rows + [nxt], len(rows))
    assert bs.settled_rows(rows + [nxt])[-1]["date"] == "2026-11-19"


def test_settled_weekend_row_accepts_friday_data():
    sat = _asof(copy.deepcopy(ROW_1119), "2026-11-20")      # Friday closes
    sat["date"] = "2026-11-21"
    sat["regime"]["stables_asof"] = "2026-11-21"             # crypto data is daily
    assert bs.settled([sat], 0)
    sat["regime"]["stables_asof"] = "2026-11-20"
    assert not bs.settled([sat], 0)


def test_settled_us_holiday_row_once_later_data_exists():
    hol = _asof(copy.deepcopy(ROW_1119), "2026-11-11")
    hol["date"] = "2026-11-11"
    hol["risk"]["hy_asof"] = "2026-11-10"                    # bond market closed
    nxt = _asof(copy.deepcopy(ROW_1119), "2026-11-12")
    nxt["date"] = "2026-11-12"
    assert not bs.settled([hol], 0) and bs.settled([hol, nxt], 0)
