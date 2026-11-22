import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import build_catalog as bc  # noqa: E402


class Catalog(unittest.TestCase):
    def test_paths_stable_and_presence(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "archive"))
        for f in ("2026-11-19.json", "2026-10-01.json"):
            open(os.path.join(d, "archive", f), "w").write("{}")
        open(os.path.join(d, "today.json"), "w").write("{}")
        rec = bc.build(d, now="2026-11-22T06:00:00Z")
        by = {r["path"]: r for r in rec["endpoints"]}
        # S10 promise: these paths never change
        for p in ("today.json", "history.csv", "tl.json", "dunya.json", "movers.json", "konum.json"):
            self.assertIn(p, by)
        self.assertTrue(by["today.json"]["exists"])
        self.assertFalse(by["history.csv"]["exists"])
        a = by["archive/{YYYY-MM-DD}.json"]
        self.assertEqual((a["first"], a["last"], a["count"]), ("2026-10-01", "2026-11-19", 2))
        for k in ("source", "site_url", "generated_at", "attribution", "license", "schema_version"):
            self.assertIn(k, rec)

    def test_licensed_inputs_are_view_only(self):
        by = {r["path"]: r for r in bc.build(tempfile.mkdtemp())["endpoints"]}
        for p in ("tl.json", "konum.json", "hafta.json", "dunya.json", "movers.json"):
            self.assertEqual(by[p]["license"], bc.VIEW)
        self.assertEqual(by["history.csv"]["license"], bc.CC)

    def test_veri_page_lists_every_endpoint(self):
        html = open(os.path.join(os.path.dirname(__file__), "..", "piyasa", "veri.html"), encoding="utf-8").read()
        for path, *_ in bc.ENDPOINTS:
            self.assertIn(path, html)
        self.assertNotIn("innerHTML", html)


if __name__ == "__main__":
    unittest.main()
