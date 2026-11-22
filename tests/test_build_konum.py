import csv, datetime as dt, json, os, re, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_konum as bk  # noqa: E402

BANNED_WORDS = re.compile(r"(?<![\wçğıöşü])(al|sat|alın|satın)(?![\wçğıöşü])")
BANNED = ["fırsat", "ucuz", "hedef", "kaçırma", "en iyi", "en kötü", "önerilir", "öneriyoruz"]


def write(path, rows, header=("date", "close")):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def days(n, end=dt.date(2026, 11, 20)):
    return [(end - dt.timedelta(days=n - 1 - i)).isoformat() for i in range(n)]


class Position(unittest.TestCase):
    def test_rising_series_is_above_all(self):
        d = days(250)
        p = bk.position({x: 100 + i for i, x in enumerate(d)})
        self.assertEqual((p["ust20"], p["ust50"], p["ust200"]), (1, 1, 1))
        # last=349, MA200 = mean(150..349)=249.5 -> +39.9%
        self.assertAlmostEqual(p["fark200"], 39.9, places=1)
        self.assertEqual(p["asof"], "2026-11-20")

    def test_short_history(self):
        d = days(60)
        p = bk.position({x: 100 - i * 0.1 for i, x in enumerate(d)})
        self.assertEqual((p["ust20"], p["ust50"]), (0, 0))
        self.assertIsNone(p["ust200"])
        self.assertIsNone(p["fark200"])
        self.assertIsNone(bk.position({x: 1.0 for x in days(10)}))


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        bk.US_DIR = os.path.join(self.tmp, "us")
        bk.TL_DIR = os.path.join(self.tmp, "tl")
        bk.CRYPTO_DIR = os.path.join(self.tmp, "c")
        bk.OUT_DIR = os.path.join(self.tmp, "derivs")
        d = days(220)
        write(os.path.join(bk.US_DIR, "ZZZ.csv"), [(x, 0, 0, 0, 50 + i, 1) for i, x in enumerate(d)],
              ("date", "open", "high", "low", "close", "volume"))
        write(os.path.join(bk.US_DIR, "AAA.csv"), [(x, 0, 0, 0, 300 - i, 1) for i, x in enumerate(d)],
              ("date", "open", "high", "low", "close", "volume"))
        old = days(220, end=dt.date(2026, 10, 1))
        write(os.path.join(bk.US_DIR, "OLD.csv"), [(x, 0, 0, 0, 10, 1) for x in old],
              ("date", "open", "high", "low", "close", "volume"))
        write(os.path.join(bk.TL_DIR, "USDTRY.csv"), [(x, 40 + i * 0.01) for i, x in enumerate(d)])
        write(os.path.join(bk.TL_DIR, "GOLD_USD.csv"), [(x, 3000) for x in d])
        self.u = {"set_date": "2026-11-22", "groups": [
            {"id": "g", "title": "Grup", "items": [
                {"id": "ZZZ", "name": "Zeta", "src": "us"}, {"id": "AAA", "name": "Alfa", "src": "us"},
                {"id": "OLD", "name": "Eski", "src": "us"}, {"id": "NONE", "name": "Yok", "src": "us"}]},
            {"id": "tr", "title": "Türkiye", "items": [
                {"id": "GRAM_ALTIN", "name": "Gram altın (TL)", "src": "tl_gram", "file": "GOLD_USD"}]}]}
        self.rec = bk.build(self.u, today=dt.date(2026, 11, 22), now="2026-11-22T06:00:00Z")

    def test_alphabetical_not_ranked(self):
        names = [r["ad"] for r in self.rec["groups"][0]["satirlar"]]
        self.assertEqual(names, ["Alfa", "Eski", "Yok", "Zeta"])

    def test_stale_and_missing(self):
        rows = {r["id"]: r for r in self.rec["groups"][0]["satirlar"]}
        self.assertTrue(rows["OLD"]["eski"])
        self.assertTrue(rows["NONE"]["eski"])
        self.assertIn("NONE", self.rec["missing"])
        self.assertFalse(rows["ZZZ"]["eski"])
        self.assertEqual(self.rec["data_date"], "2026-11-20")
        # summary counts only fresh rows with a 200-day value: Alfa (below) + Zeta (above)
        self.assertEqual(self.rec["groups"][0]["ozet"], "Grup: 2 varlığın 1 tanesi 200 günlük ortalamasının üstünde.")

    def test_gram_gold_derived(self):
        r = self.rec["groups"][1]["satirlar"][0]
        self.assertEqual(r["ust20"], 1)      # USDTRY rising, gold flat -> gram gold rising

    def test_no_prices_and_provenance(self):
        for k in ("source", "site_url", "generated_at", "attribution", "license", "schema_version"):
            self.assertIn(k, self.rec)
        allowed = {"id", "ad", "asof", "ust20", "ust50", "ust200", "fark200", "eski"}
        for g in self.rec["groups"]:
            for r in g["satirlar"]:
                self.assertLessEqual(set(r), allowed)
        text = json.dumps(self.rec, ensure_ascii=False).lower()
        for w in BANNED:
            self.assertNotIn(w, text)
        self.assertIsNone(BANNED_WORDS.search(text))

    def test_real_universe_has_no_bist_single_stocks(self):
        u = json.load(open(bk.UNIVERSE, encoding="utf-8"))
        ids = [it["id"] for g in u["groups"] for it in g["items"]]
        self.assertFalse(any(i.endswith(".IS") for i in ids))
        for need in ("SPY", "QQQ", "SMH", "GLD", "SLV", "XU100", "BTC", "ETH"):
            self.assertIn(need, ids)


if __name__ == "__main__":
    unittest.main()
