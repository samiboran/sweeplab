"""Tests for tools/build_og.py (headline card, roadmap S8)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_og as og  # noqa: E402


def test_card_lines_live_and_stale():
    t = {"status": "güncel", "data_date": "2026-11-19", "level": "KIRMIZI", "level_word": "KIRMIZI",
         "rules_version": "v1", "raw_score": 7}
    L = og.card_lines(t)
    assert L["date"] == "19 Kasım 2026" and L["level"] == "Makro hava: KIRMIZI"
    assert "7" not in L["level"]          # score only in the page's detail view
    assert "Yatırım tavsiyesi değildir." in L["foot"]
    assert og.card_lines(dict(t, status="güncellenmedi"))["note"].startswith("Güncellenmedi")


def test_runs_split_by_font_subset():
    assert og.runs("Değişim") == ["De", "ğ", "i", "ş", "im"]
    assert og.in_latin_subset("ı") and not og.in_latin_subset("İ") and not og.in_latin_subset("ş")


def test_render_and_fallback(tmp_path):
    try:
        import PIL  # noqa: F401
    except ImportError:
        return
    out = tmp_path / "og.png"
    og.render({"status": "güncel", "data_date": "2026-11-19", "level": "SARI"}, str(out))
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert os.path.exists(og.FALLBACK)
