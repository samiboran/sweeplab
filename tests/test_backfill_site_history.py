"""Tests for tools/backfill_site_history.py (retro backfill from notebook git history)."""
import csv, datetime as dt, json, os, shutil, subprocess, sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import backfill_site_history as bf  # noqa: E402
import build_site as bs  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git missing")


def make_rows(n=45):
    d0 = dt.date(2026, 9, 1)
    rows = []
    for k in range(n):
        d = (d0 + dt.timedelta(days=k)).isoformat()
        rows.append({"date": d,
                     "regime": {"stables_7d_pct": -0.5 if k % 3 else 0.4, "stables_asof": d, "netliq_musd": 5800000 - k * 1000,
                                "netliq_asof": d, "real10y": 2.5 + k * 0.01, "real10y_asof": d, "dxy": 100 + k * 0.1, "dxy_asof": d},
                     "risk": {"hy_oas": 3.0 + k * 0.01, "hy_asof": d, "vix": 15 + k * 0.2, "vix_asof": d,
                              "ndx": 25000 - k * 30, "ndx_asof": d},
                     "macro": {"gold": 4000 - k * 5, "gold_asof": d, "wti": 90 - k * 0.3, "wti_asof": d}})
    return rows


def git(repo, *a):
    subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)


def test_backfill_prepends_and_keeps_existing_rows(tmp_path):
    repo = str(tmp_path / "feed")
    os.makedirs(os.path.join(repo, "data", "derivs"))
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    rows = make_rows()
    nb = os.path.join(repo, bf.NB_PATH)
    for k in range(0, 21):                       # 21 mornings, sliding 25-row window
        json.dump({"rows": rows[k:k + 25]}, open(nb, "w"))
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", f"v{k}")
    site = os.path.join(repo, "data", "site")
    final = str(tmp_path / "final.json")
    json.dump({"rows": rows[30:45]}, open(final, "w"))
    bs.build(final, site, now=dt.datetime(2026, 10, 15, 6, tzinfo=dt.timezone.utc))
    before = open(os.path.join(site, "history.csv"), encoding="utf-8").read()
    assert before.split("\n")[1].startswith(rows[30]["date"])

    n = bf.run(repo, site, "2026-11-21T00:00:00Z")
    after = open(os.path.join(site, "history.csv"), encoding="utf-8").read()
    assert n == 10                                # rows[20..29]
    assert after.endswith(before.split("\n", 1)[1])          # existing rows verbatim
    hist = list(csv.DictReader(open(os.path.join(site, "history.csv"), encoding="utf-8")))
    assert hist[0]["date"] == rows[20]["date"] and all(h["mode"] == "retro" for h in hist[:10])
    rec = json.load(open(os.path.join(site, "archive", rows[29]["date"] + ".json"), encoding="utf-8"))
    assert rec["backfill"]["method"] == "point-in-time" and rec["mode"] == "retro"
    assert json.load(open(os.path.join(site, "archive", rows[21]["date"] + ".json")))["backfill"]["method"] == "window"
    # point-in-time comparison file
    bf.write_pit(repo, site, "2026-11-21T00:00:00Z")
    pit = [l for l in open(os.path.join(site, "retro_pit.csv"), encoding="utf-8") if not l.startswith("#")]
    assert len(pit) == 1 + 21 and pit[1].startswith(rows[24]["date"])
    # re-run adds nothing
    assert bf.run(repo, site, "2026-11-21T00:00:00Z") == 0
