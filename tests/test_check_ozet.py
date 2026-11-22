import datetime as dt, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import check_ozet as co  # noqa: E402

TODAY = dt.date(2026, 11, 23)


def good():
    return {"schema": "phd.ozet/1", "schema_version": 1, "source": "Piyasa Hava Durumu",
            "site_url": "https://samiboran.github.io/sweeplab/piyasa/", "generated_at": "2026-11-23T06:45:00Z",
            "attribution": "x", "date": "2026-11-23",
            "items": [{"konu": "Altın ve emtia", "baslik": "World Gold Council çeyrek raporunu yayımladı",
                       "ozet": "Rapora göre merkez bankalarının altın alımları sürdü.",
                       "baslik_en": "World Gold Council publishes its quarterly report",
                       "ozet_en": "According to the report, central bank gold buying continued.",
                       "kaynaklar": [{"ad": "World Gold Council", "url": "https://www.gold.org/", "zaman": "2026-11-22T08:00:00Z"}]}]}


def test_valid():
    assert co.problems(good(), TODAY) == []


def test_rejects_action_words_emoji_http_and_old_dates():
    d = good()
    d["items"][0]["ozet"] = "Altın ucuzladı, fırsat 🚀"
    d["items"][0]["kaynaklar"][0]["url"] = "http://x.com"
    d["date"] = "2026-11-10"
    p = " | ".join(co.problems(d, TODAY))
    assert "yasak kelime" in p and "emoji" in p and "https" in p and "3 gün" in p


def test_rejects_unknown_topic_and_too_many_items():
    d = good()
    d["items"][0]["konu"] = "Spor"
    assert any("konu" in x for x in co.problems(d, TODAY))
    d = good()
    d["items"] = d["items"] * 9
    assert any("1–8" in x for x in co.problems(d, TODAY))


def test_disclaimer_phrase_is_allowed():
    d = good()
    d["items"][0]["ozet"] += " Yatırım tavsiyesi değildir; öneri değildir."
    assert co.problems(d, TODAY) == []
