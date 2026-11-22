"""Tests for tools/build_week.py ('Dünyada bu Pazartesi / Cuma')."""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_week as bw  # noqa: E402


def _series(start, end, fn):
    d, out = dt.date.fromisoformat(start), {}
    while d <= dt.date.fromisoformat(end):
        if d.weekday() < 5:
            out[d.isoformat()] = fn(d)
        d += dt.timedelta(days=1)
    return out


def test_week_bounds_monday_to_sunday():
    assert bw.week_bounds(dt.date(2026, 11, 23)) == ("2026-11-23", "2026-11-29")
    assert bw.week_bounds(dt.date(2026, 11, 27)) == ("2026-11-23", "2026-11-29")


def test_window_change_uses_close_before_start():
    s = {"2025-11-21": 100.0, "2025-11-24": 101.0, "2025-11-28": 110.0, "2025-12-01": 200.0}
    assert round(bw.window_change(s, sorted(s), "2025-11-23", "2025-11-29"), 6) == 10.0


def test_same_week_history_counts_years():
    # rises 1% every weekday -> every past week is up
    s = _series("2014-01-01", "2026-11-20", lambda d: 1.01 ** (d.toordinal() - 735000))
    rows = bw.same_week_history(s, "2026-11-23", "2026-11-29", 2026)
    assert [r["year"] for r in rows] == list(range(2016, 2026))
    sm = bw.summarize(rows)
    assert sm["n"] == 10 and sm["up"] == 10 and sm["down"] == 0


def test_pick_entries_day_and_firsts():
    entries = [
        {"date": "2008-11-25", "precision": "day", "title": "a", "text": "t", "source": "s", "url": "https://x"},
        {"date": "2001-12-02", "precision": "day", "title": "b", "text": "t", "source": "s", "url": "https://x"},
        {"date": "1999-11-24", "precision": "day", "title": "no source", "text": "t", "source": "s", "url": ""},
        {"date": "1910", "precision": "year", "title": "ilk", "text": "t", "source": "s", "url": "https://x"},
    ]
    day, first = bw.pick_entries(entries, "2026-11-23", "2026-11-29", 48)
    assert [e["title"] for e in day] == ["a"]          # unsourced entry dropped, Dec 2 outside week
    assert day[0]["day_label"] == "25 Kasım" and first["title"] == "ilk"


def test_turkish_percent_format():
    assert bw.pct(1.234) == "+\u2060%1,2" and bw.pct(-0.04) == "%0,0" and bw.pct(-12.5) == "−\u2060%12,5"


def test_build_editions(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    s = _series("2014-01-01", "2026-11-26", lambda d: 100 + (d.toordinal() % 7))
    for name in ("USDTRY", "GOLD_USD", "SILVER_USD", "XU100", "SPY", "QQQ", "BTC_USD"):
        with open(raw / f"{name}.csv", "w") as f:
            f.write("date,close\n" + "".join(f"{k},{v}\n" for k, v in sorted(s.items())))
    nb = tmp_path / "nb.json"
    nb.write_text(json.dumps({"calendar": {"FOMC": ["2026-11-25"], "CPI": ["2026-12-10"]}}))
    now = dt.datetime(2026, 11, 27, 6, 0, tzinfo=dt.timezone.utc)
    tarihte = os.path.join(os.path.dirname(__file__), "..", "tools", "tarihte.json")
    rec = bw.build("cuma", dt.date(2026, 11, 27), str(raw), str(nb), tarihte, now)
    assert rec["title"] == "Dünyada bu Cuma" and rec["week_label"] == "23–29 Kasım"
    assert rec["calendar"] == [{"date": "2026-11-25", "day_label": "25 Kasım", "name": "Fed faiz kararı (FOMC)",
                                "day_label_en": "25 November", "name_en": "Fed rate decision (FOMC)"}]
    assert rec["title_en"] == "The world this Friday" and rec["week_label_en"] == "23–29 November"
    for a in rec["assets"]:
        assert a["sentence_en"] and "%" in a["sentence_en"] or "not enough" in a["sentence_en"]
        assert not any(w in a["sentence_en"].lower() for w in ("buy", "sell", "opportunity", "target"))
    assert all(a["summary"]["n"] == 10 for a in rec["assets"])
    assert all("this_week" in a for a in rec["assets"])
    assert all(e["url"].startswith("https://") for e in rec["tarihte"])
    text = json.dumps(rec, ensure_ascii=False).lower()
    for w in (" al ", " sat ", "fırsat", "ucuz", "hedef", "kaçırma"):
        assert w not in text


def test_should_build_schedule(tmp_path):
    assert bw.should_build(dt.date(2026, 11, 23), str(tmp_path), "") == "pazartesi"
    assert bw.should_build(dt.date(2026, 11, 27), str(tmp_path), "") == "cuma"
    # Wednesday with an edition for this week already -> nothing
    (tmp_path / "hafta.json").write_text(json.dumps({"week_start": "2026-11-23"}))
    assert bw.should_build(dt.date(2026, 11, 25), str(tmp_path), "") is None
    assert bw.should_build(dt.date(2026, 11, 25), str(tmp_path), "cuma") == "cuma"


def test_curated_entries_all_sourced():
    d = json.load(open(os.path.join(os.path.dirname(__file__), "..", "tools", "tarihte.json"), encoding="utf-8"))
    for e in d["entries"]:
        assert e["url"].startswith("https://") and e["source"] and e["precision"] in ("day", "year")


def test_extra_entries_from_feed(tmp_path):
    import json as _json
    base = [{"date": "2008-11-23", "title": "A"}]
    p = tmp_path / "extra.json"
    p.write_text(_json.dumps({"entries": [
        {"date": "1999-11-24", "precision": "day", "title": "B", "text": "t", "source": "s", "url": "https://x.org/"},
        {"date": "2008-11-23", "precision": "day", "title": "A", "text": "t", "source": "s", "url": "https://x.org/"},
        {"date": "2000-11-24", "precision": "day", "title": "C", "text": "t", "source": "s", "url": "http://x.org/"},
        {"date": "2001-11-24", "precision": "day", "title": "D", "text": "t", "source": "s"}]}))
    out = bw.load_extra(str(p), base)
    assert [e["title"] for e in out] == ["B"]          # duplicate, http and unsourced entries dropped
    assert bw.load_extra(str(tmp_path / "missing.json"), base) == []
