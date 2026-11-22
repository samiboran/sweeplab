import datetime as dt, json, os, re, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_dunya as bd  # noqa: E402

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "tools", "dunya_config.json"), encoding="utf-8"))
NOW = dt.datetime(2026, 11, 22, 6, 0, tzinfo=dt.timezone.utc)
TODAY = NOW.date()
BANNED_WORDS = re.compile(r"(?<![\wçğıöşü])(al|sat|alın|satın)(?![\wçğıöşü])")
BANNED = ["fırsat", "ucuz", "hedef", "kaçırma", "en iyi", "en kötü", "önerilir", "öneriyoruz"]


def rising(n=260, end=dt.date(2026, 11, 20), start=100.0, step=1.0):
    return {(end - dt.timedelta(days=n - 1 - i)).isoformat(): start + i * step for i in range(n)}


RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>x</title>
<item><title>Chip exports &amp; <b>output</b> rise</title><link>https://www.korea.net/a/1</link>
<description>BODY TEXT MUST NOT BE COPIED</description><pubDate>Sat, 21 Nov 2026 10:00:00 +0900</pubDate></item>
<item><title>Old item</title><link>https://www.korea.net/a/0</link><pubDate>Mon, 02 Nov 2026 10:00:00 GMT</pubDate></item>
<item><title>Plain http</title><link>http://insecure.example/x</link><pubDate>Sat, 21 Nov 2026 10:00:00 GMT</pubDate></item>
<item><title>javascript</title><link>javascript:alert(1)</link><pubDate>Sat, 21 Nov 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Natural gas storage report</title><link rel="alternate" href="https://www.eia.gov/x"/>
<updated>2026-11-20T15:00:00Z</updated><summary>NO BODY</summary></entry></feed>"""


class Rows(unittest.TestCase):
    def test_row_rounding_and_flags(self):
        r = bd.row_for(rising(), TODAY)
        self.assertEqual(r["asof"], "2026-11-20")
        self.assertEqual((r["ust20"], r["ust50"], r["ust200"]), (1, 1, 1))
        self.assertEqual(r["seviye"], 359.0)
        self.assertAlmostEqual(r["chg_1g"], round((359 / 358 - 1) * 100, 1))
        self.assertFalse(r["eski"])

    def test_company_rows_have_no_level(self):
        r = bd.row_for(rising(), TODAY, with_level=False)
        self.assertNotIn("seviye", r)

    def test_stale_and_empty(self):
        self.assertTrue(bd.row_for(rising(end=dt.date(2026, 11, 1)), TODAY)["eski"])
        e = bd.row_for({}, TODAY)
        self.assertIsNone(e["asof"])
        self.assertTrue(e["eski"])

    def test_partial_today_bar_dropped(self):
        s = rising(end=TODAY)
        r = bd.row_for(s, TODAY)
        self.assertEqual(r["asof"], (TODAY - dt.timedelta(days=1)).isoformat())

    def test_level_rounding(self):
        self.assertEqual(bd.nd_for(38500.4), 0)
        self.assertEqual(bd.nd_for(31.2), 2)
        self.assertEqual(bd.nd_for(0.52), 4)


class Headlines(unittest.TestCase):
    def test_only_title_source_time_link(self):
        cfg = {"feeds": [{"id": "k", "topic": "Japonya / Kore teknoloji", "source": "Korea.net", "url": "https://k/"},
                         {"id": "e", "topic": "Emtia ve madenler", "source": "EIA", "url": "https://e/"}],
               "topics": ["Japonya / Kore teknoloji", "Emtia ve madenler", "Çin"], "max_age_days": 4}
        h = bd.build_headlines(cfg, NOW, fetch=lambda u: RSS if u == "https://k/" else ATOM)
        flat = [i for t in h["konular"] for i in t["basliklar"]]
        self.assertEqual([i["baslik"] for i in flat], ["Chip exports & output rise", "Natural gas storage report"])
        for i in flat:
            self.assertEqual(set(i), {"baslik", "kaynak", "url", "zaman"})
            self.assertTrue(i["url"].startswith("https://"))
        self.assertNotIn("BODY", json.dumps(h))
        self.assertEqual(flat[0]["zaman"], "2026-11-21T01:00:00Z")
        self.assertEqual([t["konu"] for t in h["konular"]], cfg["topics"])

    def test_failing_feed_is_recorded_not_fatal(self):
        cfg = {"feeds": [{"id": "x", "topic": "Çin", "source": "X", "url": "https://x/"}], "topics": ["Çin"]}

        def boom(u):
            raise OSError("down")
        h = bd.build_headlines(cfg, NOW, fetch=boom)
        self.assertEqual(h["kaynaklar"][0]["durum"], "hata: OSError")
        self.assertEqual(h["konular"][0]["basliklar"], [])

    def test_dtd_refused(self):
        evil = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;</title></item></channel></rss>'
        with self.assertRaises(ValueError):
            bd.parse_feed(evil)

    def test_cap_total(self):
        items = b"".join(b"<item><title>T%d</title><link>https://k/%d</link><pubDate>Sat, 21 Nov 2026 0%d:00:00 GMT</pubDate></item>" % (i, i, i) for i in range(9))
        raw = b"<rss><channel>" + items + b"</channel></rss>"
        feeds = [{"id": str(n), "topic": "Çin", "source": "S", "url": "https://%d/" % n} for n in range(5)]
        h = bd.build_headlines({"feeds": feeds, "topics": ["Çin"], "max_total": 10, "max_per_feed": 3}, NOW,
                               fetch=lambda u: raw.replace(b"https://k/", u.encode()))
        self.assertEqual(len(h["konular"][0]["basliklar"]), 10)


class Build(unittest.TestCase):
    def setUp(self):
        def get(it):
            if it.get("optional"):
                return {}
            return rising()
        self.rec = bd.build(CFG, today=TODAY, now=NOW, get=get, fetch=lambda u: RSS)

    def test_provenance(self):
        r = self.rec
        for k in ("source", "site_url", "generated_at", "attribution", "license", "schema", "universe_set_date"):
            self.assertTrue(r[k], k)
        self.assertEqual(r["source"], "Piyasa Hava Durumu")
        self.assertEqual(r["data_date"], "2026-11-20")
        self.assertIn("Yalnızca görüntüleme", r["license"])

    def test_fixed_order_alphabetical_companies(self):
        self.assertEqual([m["id"] for m in self.rec["markets"]], [m["id"] for m in CFG["markets"]])
        for m in self.rec["markets"]:
            names = [c["ad"].casefold() for c in m["sirketler"]]
            self.assertEqual(names, sorted(names))
            self.assertTrue(5 <= len(names) <= 10)
            for c in m["sirketler"]:
                self.assertNotIn("seviye", c)

    def test_optional_missing_index_dropped(self):
        jp = self.rec["markets"][0]
        self.assertNotIn("TOPIX", [i["id"] for i in jp["endeksler"]])
        self.assertIn("TOPIX", self.rec["missing"])

    def test_reference_metals_no_prices(self):
        for r in self.rec["referans_metaller"]:
            self.assertEqual(set(r), {"ad", "aciklama", "durum"})
            self.assertEqual(r["durum"], "günlük serbest veri yok")

    def test_commodities_present_with_units(self):
        ids = {r["id"] for g in self.rec["emtia"] for r in g["satirlar"]}
        self.assertTrue({"GC", "SI", "PL", "PA", "HG", "CL", "BZ", "NG"} <= ids)
        for g in self.rec["emtia"]:
            for r in g["satirlar"]:
                self.assertTrue(r["birim"])

    def test_no_action_words(self):
        txt = json.dumps({k: v for k, v in self.rec.items() if k != "basliklar"}, ensure_ascii=False).casefold()
        txt += " " + json.dumps(self.rec["basliklar"]["not"], ensure_ascii=False).casefold()
        for w in BANNED:
            self.assertNotIn(w, txt)
        self.assertIsNone(BANNED_WORDS.search(txt))

    def test_no_secret_or_raw_candles(self):
        txt = json.dumps(self.rec)
        self.assertNotIn("open", txt.lower().replace("opendata", ""))
        self.assertNotIn("volume", txt.lower())


if __name__ == "__main__":
    unittest.main()
