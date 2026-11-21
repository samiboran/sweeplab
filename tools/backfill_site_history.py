"""One-off (re-runnable) retro backfill for data/site/history.csv from the notebook's
git history on data-feed (kept since 2026-10-08). Private engine.

For each date D older than the first history.csv row:
  - use the newest stored notebook version in which D is SETTLED (every daily input
    is from D's own business day; build_site.settled) and has a full 20-row lookback.
    A morning's newest row is not used: it still carries the previous day's US data;
  - score with rules v1 (build_site.score_row), mode "retro", noise filter applied in
    date order within the backfilled segment.
Existing history rows are kept byte-for-byte (never rewritten); new rows are only
added BEFORE them. Archive files are written only if missing.

Usage (inside a data-feed checkout with history):
  python3 tools/backfill_site_history.py <feed_repo_dir>
"""
import csv, io, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import build_site as bs  # noqa: E402

NB_PATH = "data/derivs/notebook_daily.json"


def versions(repo):
    out = subprocess.run(["git", "-C", repo, "log", "--reverse", "--format=%H %cI", "--", NB_PATH],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    for line in filter(None, out):
        sha, when = line.split(" ", 1)
        try:
            blob = subprocess.run(["git", "-C", repo, "show", f"{sha}:{NB_PATH}"],
                                  capture_output=True, text=True, check=True).stdout
            rows = sorted(json.loads(blob)["rows"], key=lambda r: r["date"])
        except Exception:
            continue
        if rows:
            yield sha, when, rows


def complete(row):
    return all(bs.get(row, p) is not None for p, _, _ in bs.CORE_INPUTS.values())


def pick(vers, before):
    """{date: (rows, index, sha)} for dates < before: the NEWEST stored notebook version
    in which the date is settled (all daily inputs from that day) with a full 20-row
    lookback — i.e. the most complete data we kept for that day."""
    out = {}
    for sha, _, rows in vers:                   # oldest -> newest; newer wins
        for i in range(bs.LOOKBACK, len(rows)):
            d = rows[i]["date"]
            if d < before and complete(rows[i]) and bs.settled(rows, i):
                out[d] = (rows, i, sha)
    return out


def run(repo, site, generated_at):
    hpath = os.path.join(site, "history.csv")
    raw = open(hpath, encoding="utf-8").read()
    hist = list(csv.DictReader(io.StringIO(raw)))
    first = hist[0]["date"]
    chosen = pick(list(versions(repo)), first)
    if not chosen:
        print("nothing to backfill")
        return 0
    prev_pub = prev_raw = prev_h = None
    new_rows = []
    for d in sorted(chosen):
        rows, i, sha = chosen[d]
        s = bs.score_row(rows, i)
        level, held = bs.publish_level(prev_pub, prev_raw, s["raw_level"])
        rec = bs.build_record(s, level, held, "retro", generated_at, d, bs.inputs_asof(rows[i]))
        rec["backfill"] = {"method": "settled", "notebook_version": sha[:7],
                           "note": "Geriye dönük: saklanan veri sürümlerinden o güne ait tamamlanmış veriyle v1 kurallarına göre sonradan hesaplandı."}
        h = bs.history_row(rec)
        rec["answers"] = bs.answers(rec, prev_h)
        bs.write_json(os.path.join(site, "archive", f"{d}.json"), rec, overwrite=False)
        new_rows.append(h)
        prev_pub, prev_raw, prev_h = level, s["raw_level"], h
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=bs.HISTORY_FIELDS, lineterminator="\n")
    w.writeheader()
    for r in new_rows:
        w.writerow(r)
    header, rest = raw.split("\n", 1)
    assert header == buf.getvalue().split("\n", 1)[0], "history header changed"
    with open(hpath + ".tmp", "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue() + rest)          # existing rows appended verbatim
    os.replace(hpath + ".tmp", hpath)
    print(f"backfilled {len(new_rows)} days: {min(chosen)}..{max(chosen)}")
    return len(new_rows)


def rebuild(repo, site, generated_at, note):
    """Documented one-time correction: recompute ALL retro rows from the newest settled
    data with a full 20-row lookback. Refuses to run once any live row exists (published
    live scores are never rewritten). Changed archive files get a "duzeltme" note;
    archive files for dates that are no longer scored (unsettled) are removed."""
    hpath = os.path.join(site, "history.csv")
    old = {r["date"]: r for r in csv.DictReader(open(hpath, encoding="utf-8"))} if os.path.exists(hpath) else {}
    if any(r.get("mode") == "live" for r in old.values()):
        raise SystemExit("live rows exist; rebuild refused")
    chosen = pick(list(versions(repo)), "9999-12-31")
    prev_pub = prev_raw = prev_h = None
    rows_out, changed = [], []
    for d in sorted(chosen):
        rows, i, sha = chosen[d]
        s = bs.score_row(rows, i)
        level, held = bs.publish_level(prev_pub, prev_raw, s["raw_level"])
        rec = bs.build_record(s, level, held, "retro", generated_at, d, bs.inputs_asof(rows[i]))
        rec["backfill"] = {"method": "settled", "notebook_version": sha[:7],
                           "note": "Geriye dönük: saklanan veri sürümlerinden o güne ait tamamlanmış veriyle v1 kurallarına göre sonradan hesaplandı."}
        h = bs.history_row(rec)
        rec["answers"] = bs.answers(rec, prev_h)
        o = old.get(d)
        key = lambda r: tuple(str(r.get(k, "")) for k in ["raw_score", "level", "level_held"] + bs.RULE_CODES)
        apath = os.path.join(site, "archive", f"{d}.json")
        if o is None or key(o) != key(h) or not os.path.exists(apath):
            if o is not None:
                rec["duzeltme"] = {"date": generated_at[:10], "note": note,
                                   "onceki": {"raw_score": int(o["raw_score"]), "level": o["level"]}}
                changed.append(d)
            bs.write_json(apath, rec)
        rows_out.append(h)
        prev_pub, prev_raw, prev_h = level, s["raw_level"], h
    removed = sorted(set(old) - set(chosen))
    for d in removed:
        p = os.path.join(site, "archive", f"{d}.json")
        if os.path.exists(p):
            os.remove(p)
    with open(hpath + ".tmp", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=bs.HISTORY_FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows_out:
            w.writerow(r)
    os.replace(hpath + ".tmp", hpath)
    print(f"rebuilt {len(rows_out)} days {min(chosen)}..{max(chosen)}; corrected {changed}; removed {removed}")
    return changed, removed


if __name__ == "__main__":
    import datetime as dt
    repo = sys.argv[1]
    site = os.path.join(repo, "data", "site")
    ga = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if "--rebuild" in sys.argv:
        rebuild(repo, site, ga, sys.argv[sys.argv.index("--rebuild") + 1])
    else:
        run(repo, site, ga)
