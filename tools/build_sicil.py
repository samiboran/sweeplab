#!/usr/bin/env python3
"""Piyasa Hava Durumu — "Sicil" (track record) builder.

Reads the published level history (data/site/history.csv) and the private notebook
(Nasdaq Composite closes; licensed input, never published) and writes
data/site/sicil.json with ONLY derived words: for every published switch to KIRMIZI,
whether it was followed by a drawdown ("teyit edildi") or not ("yanlış alarm"),
plus "kaçırılan düşüş" episodes that happened while the level was never KIRMIZI.

Check (explained in plain words in piyasa/yontem.html#sicil):
  * Signal  = first day of a published KIRMIZI run (level changed to KIRMIZI).
  * Teyit   = within the next 20 calendar days the Nasdaq Composite closes at
              least 5% below its close on the signal day.
  * Yanlış alarm = 20 days passed without that.
  * Bekliyor = fewer than 20 days of data after the signal.
  * Kaçırılan düşüş = Nasdaq closes at least 10% below its highest close of the previous
              20 days, and the published level was not KIRMIZI on any of those days.

Append-only: a final result (teyit / yanlış alarm / kaçırılan) is never rewritten;
only "bekliyor" entries are updated. Non-fatal step in daily-brief.yml.
"""
import csv
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site as bs  # noqa: E402

SITE_OUT = os.environ.get("SITE_OUT", "data/site")
NOTEBOOK = bs.NOTEBOOK
SHOW_FROM = "2026-10-01"      # Boran: archive / sicil shown from October 2026
WINDOW = 20                   # calendar days after the signal
CONFIRM_DROP = -5.0           # % vs signal-day close
MISS_DROP = -10.0             # % vs highest close of previous 20 days
FINAL = {"teyit edildi", "yanlış alarm", "kaçırılan düşüş"}


def _d(s):
    return dt.date.fromisoformat(str(s)[:10])


def ndx_series(rows):
    """{date: close} using only rows whose Nasdaq value is from that day or earlier."""
    out = {}
    for r in rows:
        v = bs.get(r, "risk.ndx")
        if v is not None:
            out[r["date"]] = float(v)
    return out


def signals(hist):
    """First day of each published KIRMIZI run."""
    out, prev = [], None
    for h in hist:
        if h["level"] == "KIRMIZI" and prev != "KIRMIZI":
            out.append(h)
        prev = h["level"]
    return out


def evaluate(sig_date, ndx, last_data_date):
    base = ndx.get(sig_date)
    if base is None:
        return None
    end = (_d(sig_date) + dt.timedelta(days=WINDOW)).isoformat()
    after = [(d, v) for d, v in sorted(ndx.items()) if sig_date < d <= end]
    hit = next((d for d, v in after if (v / base - 1) * 100 <= CONFIRM_DROP), None)
    if hit:
        return {"result": "teyit edildi", "confirm_date": hit,
                "days_to_confirm": (_d(hit) - _d(sig_date)).days}
    if last_data_date >= end and after:
        return {"result": "yanlış alarm", "checked_until": end}
    return {"result": "bekliyor", "checked_until": last_data_date}


def misses(hist, ndx):
    level = {h["date"]: h["level"] for h in hist}
    dates = sorted(ndx)
    out, in_episode = [], False
    for d in dates:
        lo = (_d(d) - dt.timedelta(days=WINDOW)).isoformat()
        prev = [ndx[x] for x in dates if lo <= x < d]
        if not prev or d not in level:
            in_episode = False
            continue
        dd = (ndx[d] / max(prev) - 1) * 100
        window_lv = [level.get(x) for x in dates if lo <= x <= d]
        if dd <= MISS_DROP and "KIRMIZI" not in window_lv:
            if not in_episode:
                out.append({"date": d, "result": "kaçırılan düşüş", "level": level[d],
                            "mode": next((h["mode"] for h in hist if h["date"] == d), "retro")})
            in_episode = True
        else:
            in_episode = False
    return out


def build(site=SITE_OUT, notebook=NOTEBOOK, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    hist = bs.read_history(os.path.join(site, "history.csv"))
    rows = sorted(json.load(open(notebook, encoding="utf-8"))["rows"], key=lambda x: x["date"])
    rows = bs.settled_rows(rows)
    ndx = ndx_series(rows)
    last = rows[-1]["date"] if rows else "0000-00-00"
    path = os.path.join(site, "sicil.json")
    old = {}
    if os.path.exists(path):
        for e in json.load(open(path, encoding="utf-8")).get("entries", []):
            old[(e["date"], e["kind"])] = e

    entries = dict(old)
    for h in signals(hist):
        key = (h["date"], "sinyal")
        if key in old and old[key]["result"] in FINAL:
            continue
        ev = evaluate(h["date"], ndx, last)
        if ev is None:
            if key not in old:
                entries[key] = {"date": h["date"], "kind": "sinyal", "level": "KIRMIZI",
                                "mode": h["mode"], "rules_version": h["rules_version"],
                                "result": "değerlendirilemedi"}
            continue
        e = {"date": h["date"], "kind": "sinyal", "level": "KIRMIZI", "mode": h["mode"],
             "rules_version": h["rules_version"]}
        e.update(ev)
        entries[key] = e
    for m in misses(hist, ndx):
        key = (m["date"], "kaçırılan")
        if key not in old:
            m["kind"] = "kaçırılan"
            entries[key] = m

    shown = sorted((e for e in entries.values() if e["date"] >= SHOW_FROM), key=lambda e: e["date"])
    live = [e for e in shown if e.get("mode") == "live"]
    summary = {
        "canli_sinyal": sum(1 for e in live if e["kind"] == "sinyal"),
        "canli_teyit": sum(1 for e in live if e.get("result") == "teyit edildi"),
        "canli_yanlis_alarm": sum(1 for e in live if e.get("result") == "yanlış alarm"),
        "canli_bekliyor": sum(1 for e in live if e.get("result") == "bekliyor"),
        "canli_kacirilan": sum(1 for e in live if e["kind"] == "kaçırılan"),
    }
    out = bs.provenance(now.replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    out.update({
        "rules_version": bs.RULES_VERSION,
        "freeze_date": bs.FREEZE_DATE,
        "show_from": SHOW_FROM,
        "data_until": last,
        "check": {"window_days": WINDOW, "confirm_drop_pct": CONFIRM_DROP, "miss_drop_pct": MISS_DROP,
                  "reference": "Nasdaq Bileşik kapanışı (lisanslı; değer yayımlanmaz)"},
        "summary_live": summary,
        "entries": shown + [e for e in sorted(entries.values(), key=lambda e: e["date"])
                            if e["date"] < SHOW_FROM],
        "disclaimer": bs.DISCLAIMER,
    })
    bs.write_json(path, out)
    return summary


def main():
    try:
        print(json.dumps(build(), ensure_ascii=False))
    except Exception as e:  # non-fatal
        print(f"sicil build failed: {type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
