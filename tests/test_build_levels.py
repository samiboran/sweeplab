import datetime as dt, json, os, re, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_levels as bl  # noqa: E402

BANNED = re.compile(r"(?<![\wçğıöşü])(al|sat|alın|satın|fırsat|ucuz|ucuzladı|hedef|kaçırma|öneri|buy|sell|target|cheap|opportunity)(?![\wçğıöşü])", re.I)


def series(values, end=dt.date(2026, 11, 20)):
    n = len(values)
    return {(end - dt.timedelta(days=n - 1 - i)).isoformat(): v for i, v in enumerate(values)}


def zigzag(n=300, lo=100.0, hi=120.0, period=40):
    out = []
    for i in range(n):
        ph = (i % period) / period
        out.append(lo + (hi - lo) * (2 * ph if ph < 0.5 else 2 - 2 * ph))
    return out


class Engine(unittest.TestCase):
    def test_swings_find_tops_and_bottoms(self):
        cs = zigzag(200)
        kinds = {k for _, k in bl.swings(cs)}
        self.assertEqual(kinds, {"tepe", "dip"})

    def test_range_gives_resistance_above_and_support_below(self):
        cs = zigzag(300) + [110.0, 110.5, 110.2]
        r = bl.analyse(series(cs))
        self.assertTrue(r["above"] and r["below"])
        self.assertAlmostEqual(r["above"][0]["price"], 120.0, delta=1.0)
        self.assertAlmostEqual(r["below"][0]["price"], 100.0, delta=1.0)
        self.assertGreaterEqual(r["above"][0]["touches"], 2)

    def test_rejection_event_is_resistance(self):
        base = zigzag(280)                                  # ends rising from the bottom
        tail = [112, 115, 118, 119.8, 119.5, 117, 114, 111, 108, 106, 105]
        r = bl.analyse(series(base + tail))
        kinds = [e["kind"] for e in r["events"]]
        self.assertIn("direnc_oldu", kinds)

    def test_breakout_event_dated_at_the_cross(self):
        base = zigzag(280)
        tail = [110, 113, 116, 118, 121, 125, 128, 130, 131, 132, 133]
        r = bl.analyse(series(base + tail))
        ev = [e for e in r["events"] if e["kind"] == "ustune_cikti"]
        self.assertTrue(ev)
        self.assertLess(ev[0]["date"], r["asof"])          # crossing day, not simply today

    def test_short_series_is_skipped(self):
        self.assertIsNone(bl.analyse(series([1.0 + i for i in range(30)])))

    def test_tolerance_bounds(self):
        self.assertEqual(bl.tolerance([100.0] * 200), 0.004)
        self.assertEqual(bl.tolerance([100.0 if i % 2 else 130.0 for i in range(200)]), 0.04)


class Public(unittest.TestCase):
    def setUp(self):
        cs = zigzag(300) + [110.0, 110.5, 110.2]
        raw = {"BRENT_USD": series(cs), "SPY": series(cs), "GOLD_USD": series(cs), "USDTRY": series([40.0] * len(cs))}
        self.rec = bl.build(raw, today=dt.date(2026, 11, 21))

    def test_fund_levels_are_percent_only(self):
        spy = [a for a in self.rec["assets"] if a["id"] == "spy"][0]
        self.assertFalse(spy["abs"])
        self.assertNotIn("close", spy)
        for z in spy["direnc"] + spy["destek"]:
            self.assertNotIn("p", z)
        self.assertEqual(spy["series"][0][1], 100.0)

    def test_price_assets_carry_prices_and_gram_is_derived(self):
        by = {a["id"]: a for a in self.rec["assets"]}
        self.assertIn("p", by["brent"]["direnc"][0])
        self.assertAlmostEqual(by["gram_altin"]["close"], round(110.2 * 40 / 31.1035), delta=1)

    def test_chain_order_and_missing(self):
        ids = [c["id"] for c in self.rec["chain"]]
        self.assertEqual(ids, ["brent", "ons_altin", "spy"])     # others have no data here
        self.assertIn("btc", self.rec["missing"])

    def test_no_action_words(self):
        txt = json.dumps(self.rec, ensure_ascii=False)
        self.assertIsNone(BANNED.search(txt.replace("satır", "")), BANNED.search(txt))

    def test_provenance(self):
        for k in ("schema", "source", "site_url", "generated_at", "attribution", "license", "disclaimer"):
            self.assertTrue(self.rec[k])

    def test_fred_parser(self):
        self.assertEqual(bl.parse_fred("observation_date,DGS10\n2026-11-19,4.41\n2026-11-20,.\n"), {"2026-11-19": 4.41})


if __name__ == "__main__":
    unittest.main()
