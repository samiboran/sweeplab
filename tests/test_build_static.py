"""Tests for tools/build_static.py (crawler snapshots)."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_site as bs  # noqa: E402
import build_static as bst  # noqa: E402

PIYASA = os.path.join(os.path.dirname(__file__), "..", "piyasa")


def _rec(day, level="KIRMIZI"):
    return {"data_date": day, "publish_date": day, "level": level, "mode": "retro", "rules_version": "v1",
            "raw_score": 7, "max_score": 9, "compare_date": "2026-10-01", "generated_at": "2026-11-21T06:00:00Z",
            "rules": [{"code": "L1", "group": "Likidite", "title": "Stablecoin arzı", "flag": 1,
                       "sentence": "Stablecoin <arzı> azaldı."}],
            "answers": [{"q": "Bugün makro hava nasıl?", "a": ["Seviye KIRMIZI."]}]}


def test_snapshots_and_sitemap(tmp_path):
    dist = tmp_path / "dist"
    shutil.copytree(PIYASA, dist)
    data = dist / "data" / "site"
    (data / "archive").mkdir(parents=True)
    rows = []
    for day, lv in [("2026-09-30", "SARI"), ("2026-10-20", "SARI"), ("2026-10-21", "KIRMIZI")]:
        (data / "archive" / f"{day}.json").write_text(json.dumps(_rec(day, lv)), encoding="utf-8")
        rows.append({k: "" for k in bs.HISTORY_FIELDS} | {"date": day, "level": lv, "rules_version": "v1",
                                                          "mode": "retro", "raw_score": "7", "L1": "1"})
    bs.append_history(str(data / "history.csv"), rows)
    (data / "today.json").write_text(json.dumps(_rec("2026-10-21")), encoding="utf-8")

    res = bst.build(str(dist), base="https://example.org/")
    assert res["days"] == 2                      # 2026-09-30 is before SHOW_FROM
    idx = (dist / "index.html").read_text(encoding="utf-8")
    assert "21 Ekim 2026 — Makro hava: KIRMIZI" in idx
    assert "Stablecoin &lt;arzı&gt; azaldı." in idx   # escaped, never raw markup
    assert '<link rel="canonical" href="https://example.org/">' in idx
    page = (dist / "arsiv" / "2026-10-20.html").read_text(encoding="utf-8")
    assert "script-src 'none'" in page and "<script" not in page
    assert "Yatırım tavsiyesi değildir." in page
    sm = (dist / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://example.org/arsiv/2026-10-21.html" in sm and "2026-09-30" not in sm
    assert "Sitemap: https://example.org/sitemap.xml" in (dist / "robots.txt").read_text(encoding="utf-8")
    assert "arsiv/2026-10-21.html" in (dist / "arsiv.html").read_text(encoding="utf-8")


def test_verification_meta(tmp_path):
    import build_static as bst
    c = tmp_path / "config.js"
    c.write_text('window.PHD_CONFIG = {verification: { google: "abcDEF123_-xyz", bing: "" }};')
    assert bst.verification_meta(str(c)) == '<meta name="google-site-verification" content="abcDEF123_-xyz">'
    c.write_text('window.PHD_CONFIG = {verification: { google: "\\"><script>", bing: "0123456789ABCDEF" }};')
    assert bst.verification_meta(str(c)) == '<meta name="msvalidate.01" content="0123456789ABCDEF">'
    c.write_text('window.PHD_CONFIG = {verification: { google: "", bing: "" }};')
    assert bst.verification_meta(str(c)) == ""
