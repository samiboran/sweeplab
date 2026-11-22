import datetime as dt, json, os, re, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_movers as bm  # noqa: E402

CFG = json.load(open(bm.CONFIG, encoding="utf-8"))
TODAY = dt.date(2026, 11, 22)
BANNED = re.compile(r"(?<![\wçğıöşü])(al|sat|alın|satın|fırsat|ucuz|ucuzladı|hedef|kaçırma|öneri(?!\s*değil))(?![\wçğıöşü])")


def flat(n=300, end=dt.date(2026, 11, 20), px=100.0, vol=1_000_000):
    out = {}
    for i in range(n):
        d = (end - dt.timedelta(days=n - 1 - i)).isoformat()
        p = px * (1 + 0.002 * ((i % 5) - 2))          # small wiggle, ATR > 0
        out[d] = (p, p * 1.01, p * 0.99, p, vol)
    return out


class Analyse(unittest.TestCase):
    def test_volume_gap_atr_high_reasons(self):
        s = flat()
        last = max(s)
        prev_c = s[sorted(s)[-2]][3]
        s[last] = (prev_c * 1.07, prev_c * 1.25, prev_c * 1.06, prev_c * 1.20, 4_200_000)
        r = bm.analyse("XYZ", s, -1.0, CFG, False, TODAY)
        self.assertEqual(r["chg_1g"], 20.0)
        self.assertEqual(set(r["tur"]), {"hacim", "bosluk", "atr", "zirve", "ters"})
        self.assertIn("Hacim 20 günlük ortalamanın 4,2 katı", r["gerekce"])
        self.assertIn("Açılış boşluğu +%7,0 (önceki kapanışa göre)", r["gerekce"])

    def test_today_bar_is_ignored(self):
        s = flat(end=TODAY)                              # includes a bar dated "today" (incomplete)
        r = bm.analyse("XYZ", s, None, CFG, False, TODAY)
        self.assertEqual(r["asof"], "2026-11-21")

    def test_closed_session_uses_today_bar(self):
        bist = next(m for m in CFG["markets"] if m["id"] == "bist")
        kripto = next(m for m in CFG["markets"] if m["id"] == "kripto")
        fri = dt.date(2026, 11, 20)
        before = dt.datetime(2026, 11, 20, 7, 30, tzinfo=dt.timezone.utc)
        after = dt.datetime(2026, 11, 20, 15, 30, tzinfo=dt.timezone.utc)
        self.assertEqual(bm.cutoff(bist, fri, before), fri)                       # 10:30 İstanbul: session open
        self.assertEqual(bm.cutoff(bist, fri, after), fri + dt.timedelta(days=1))  # 18:30: closed → today's bar used
        self.assertEqual(bm.cutoff(kripto, fri, after), fri)                       # crypto: never before UTC midnight
        self.assertEqual(bm.cutoff(bist, TODAY, dt.datetime(2026, 11, 22, 16, 0, tzinfo=dt.timezone.utc)), TODAY)  # Sunday
        s = flat(end=fri)
        r = bm.build_market(bist, CFG, fri, {"XYZ": s}, {d: v[3] for d, v in s.items()}, after)
        self.assertEqual(r["asof"], "2026-11-20")
        r = bm.build_market(bist, CFG, fri, {"XYZ": s}, {d: v[3] for d, v in s.items()}, before)
        self.assertEqual(r["asof"], "2026-11-19")

    def test_crypto_gap_threshold_is_wider(self):
        s = flat()
        last = max(s)
        pc = s[sorted(s)[-2]][3]
        s[last] = (pc * 1.06, pc * 1.07, pc * 1.05, pc * 1.06, 1_000_000)
        self.assertIn("bosluk", bm.analyse("A", dict(s), None, CFG, False, TODAY)["tur"])
        self.assertNotIn("bosluk", bm.analyse("A", dict(s), None, CFG, True, TODAY)["tur"])


class Market(unittest.TestCase):
    def setUp(self):
        self.m = [x for x in CFG["markets"] if x["id"] == "abd"][0]
        series = {}
        for i, sym in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG"]):
            s = flat(px=50.0, vol=10_000_000)
            last = max(s)
            pc = s[sorted(s)[-2]][3]
            k = 1 + (i - 3) / 100.0
            s[last] = (pc, pc * max(k, 1) * 1.001, pc * min(k, 1) * 0.999, pc * k, 10_000_000)
            series[sym] = s
        series["THIN"] = flat(px=50.0, vol=10)                 # below liquidity floor
        series["PENNY"] = flat(px=2.0, vol=500_000_000)        # below min price
        old = flat(end=dt.date(2026, 11, 10), px=50.0, vol=10_000_000)
        series["OLD"] = old                                    # stopped updating: never a "today's mover"
        idx = {d: v[3] for d, v in flat().items()}
        self.rec = bm.build_market(self.m, CFG, TODAY, series, idx)

    def test_lists_and_floor(self):
        r = self.rec
        self.assertEqual([x["sembol"] for x in r["yukselenler"]], ["GGG", "FFF", "EEE"])
        self.assertEqual([x["sembol"] for x in r["dusenler"]], ["AAA", "BBB", "CCC"])
        self.assertEqual(r["likidite_disi"], 2)
        syms = json.dumps(r)
        for s in ("THIN", "PENNY", "OLD"):
            self.assertNotIn(s, syms)
        for x in r["yukselenler"] + r["dusenler"]:
            self.assertEqual(x["neden"], bm.NEDEN)
            self.assertLessEqual(set(x), {"sembol", "chg_1g", "rel_hacim", "neden"})

    def test_stale_market_shows_nothing(self):
        r = bm.build_market(self.m, CFG, dt.date(2026, 12, 15), {"AAA": flat()}, {})
        self.assertTrue(r["eski"])
        self.assertEqual(r["yukselenler"] + r["dusenler"] + r["anomaliler"], [])

    def test_record_provenance_and_wording(self):
        rec = bm.build(CFG, today=TODAY, now="2026-11-22T06:00:00Z",
                       inputs={m["id"]: ({}, {}) for m in CFG["markets"]})
        for k in ("source", "site_url", "generated_at", "attribution", "license", "schema_version"):
            self.assertIn(k, rec)
        self.assertIsNone(BANNED.search(json.dumps(rec, ensure_ascii=False).lower()))
        self.assertIsNone(BANNED.search(json.dumps(self.rec, ensure_ascii=False).lower()))


if __name__ == "__main__":
    unittest.main()
