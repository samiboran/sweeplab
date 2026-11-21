"""One-off (re-runnable) retro backfill for data/site/history.csv from the notebook's
git history on data-feed (kept since 2026-10-08). Private engine.

For each date D older than the first history.csv row:
  - use the earliest notebook version in which D was the LAST row (point-in-time:
    what was known that morning); otherwise the earliest version where D has a full
    20-row lookback (index >= 20);
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
    """{date: (rows, index, sha)} for dates < before."""
    last_row, full = {}, {}
    for sha, _, rows in vers:
        d = rows[-1]["date"]
        if d < before and d not in last_row and len(rows) > bs.LOOKBACK and complete(rows[-1]):
            last_row[d] = (rows, len(rows) - 1, sha)
        for i in range(bs.LOOKBACK, len(rows)):
            d = rows[i]["date"]
            if d < before and d not in full and complete(rows[i]):
                full[d] = (rows, i, sha)
    out = dict(full)
    out.update(last_row)          # point-in-time wins
    return out, set(last_row)


def run(repo, site, generated_at):
    hpath = os.path.join(site, "history.csv")
    raw = open(hpath, encoding="utf-8").read()
    hist = list(csv.DictReader(io.StringIO(raw)))
    first = hist[0]["date"]
    chosen, pit = pick(list(versions(repo)), first)
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
        rec["backfill"] = {"method": "point-in-time" if d in pit else "window",
                           "note": "Geriye dönük: o tarihte saklanan veri sürümüyle v1 kurallarına göre sonradan hesaplandı."}
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
    print(f"backfilled {len(new_rows)} days: {min(chosen)}..{max(chosen)} "
          f"({len(pit & set(chosen))} point-in-time)")
    return len(new_rows)


def write_pit(repo, site, generated_at):
    """data/site/retro_pit.csv: every date that was the last notebook row of some morning,
    scored with THAT morning's data (point-in-time). Comparison file for the track record;
    history.csv is not changed by it."""
    chosen, pit = pick(list(versions(repo)), "9999-12-31")
    path = os.path.join(site, "retro_pit.csv")
    fields = ["date", "rules_version", "method", "raw_score", "raw_level"] + bs.RULE_CODES + ["generated_at"]
    with open(path + ".tmp", "w", encoding="utf-8", newline="") as f:
        f.write(f"# {bs.SOURCE} — geriye dönük, o sabahki veriyle (point-in-time) v1 skorları. {bs.ATTRIBUTION}\n")
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for d in sorted(pit):
            rows, i, _ = chosen[d]
            sc = bs.score_row(rows, i)
            row = {"date": d, "rules_version": bs.RULES_VERSION, "method": "point-in-time",
                   "raw_score": sc["raw_score"], "raw_level": sc["raw_level"], "generated_at": generated_at}
            row.update({k: "" if sc["flags"][k] is None else sc["flags"][k] for k in bs.RULE_CODES})
            w.writerow(row)
    os.replace(path + ".tmp", path)
    print(f"retro_pit.csv: {len(pit)} days")


if __name__ == "__main__":
    import datetime as dt
    repo = sys.argv[1]
    site = os.path.join(repo, "data", "site")
    ga = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if "--pit-only" not in sys.argv:
        run(repo, site, ga)
    write_pit(repo, site, ga)
