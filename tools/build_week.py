"""'Dünyada bu Pazartesi' / 'Dünyada bu Cuma' — weekly editions for Piyasa Hava Durumu.

Private engine; publishes DERIVED data only (percent changes, counts, medians):
  data/site/hafta.json                latest edition
  data/site/hafta/YYYY-MM-DD.json     one file per edition (never rewritten)

Pazartesi: how the same calendar week (e.g. 23–29 Kasım) went in each of the past
  10 years for gram altın, gram gümüş, dolar/TL, BIST 100 (dolar bazında), SPY, QQQ,
  BTC; this week's scheduled US data releases; sourced economic-history entries.
Cuma: the same table plus this week's change so far (last close available Friday
  morning, i.e. through Thursday for exchanges) and where it sits among past years.

Inputs (private, data-feed): data/research/tl_1d/*.csv (date,close),
data/derivs/notebook_daily.json (calendar), tools/tarihte.json (curated, every entry
sourced). Runs daily; writes only on Monday/Friday (Istanbul) or when the current
week has no edition yet. FORCE_EDITION=pazartesi|cuma overrides (manual runs).
No forecasts, no recommendations: past same-week moves are shown as history only.
"""
import csv
import datetime as dt
import json
import os
import statistics
import sys

RAW_DIR = os.environ.get("TL_RAW_DIR", "data/research/tl_1d")
SITE_OUT = os.environ.get("SITE_OUT", "data/site")
NOTEBOOK = os.environ.get("NOTEBOOK", "data/derivs/notebook_daily.json")
TARIHTE = os.environ.get("TARIHTE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "tarihte.json"))
# Extra entries added by the daily-digest scheduled task on data-feed (no PR needed); same schema.
TARIHTE_EXTRA = os.environ.get("TARIHTE_EXTRA", "")
YEARS = 10
OZ_GRAM = 31.1035
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri, CC BY 4.0"
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
          "Eylül", "Ekim", "Kasım", "Aralık"]
CAL_NAMES = {"FOMC": "Fed faiz kararı (FOMC)", "CPI": "ABD enflasyon verisi (TÜFE)",
             "NFP": "ABD tarım dışı istihdam verisi"}
DISCLAIMER = ("Geçmiş yıllardaki hareketler yalnız tarihsel bilgidir; gelecek hakkında bir şey söylemez. "
              "Yatırım tavsiyesi değildir.")


# ---------------------------------------------------------------- data
def read_csv(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[row["date"]] = float(row["close"])
            except (KeyError, ValueError, TypeError):
                continue
    return out


def combine(a, b, fn):
    """Series on a's dates with b forward-filled."""
    out, bd, j, last = {}, sorted(b), 0, None
    for d in sorted(a):
        while j < len(bd) and bd[j] <= d:
            last = b[bd[j]]
            j += 1
        if last is not None:
            out[d] = fn(a[d], last)
    return out


def load_assets(raw_dir):
    r = {k: read_csv(os.path.join(raw_dir, k + ".csv"))
         for k in ("USDTRY", "GOLD_USD", "SILVER_USD", "XU100", "SPY", "QQQ", "BTC_USD")}
    usd = r["USDTRY"]
    return [
        ("gram_altin", "Gram altın (TL)", combine(r["GOLD_USD"], usd, lambda g, u: g * u / OZ_GRAM) if usd else {}),
        ("gram_gumus", "Gram gümüş (TL)", combine(r["SILVER_USD"], usd, lambda s, u: s * u / OZ_GRAM) if usd else {}),
        ("dolar", "Dolar/TL", usd),
        ("bist100_usd", "BIST 100 (dolar bazında)", combine(r["XU100"], usd, lambda x, u: x / u) if usd else {}),
        ("spy", "S&P 500 fonu (SPY)", r["SPY"]),
        ("qqq", "Nasdaq 100 teknoloji fonu (QQQ)", r["QQQ"]),
        ("btc", "Bitcoin (dolar)", r["BTC_USD"]),
    ]


# ---------------------------------------------------------------- calc
def close_on_or_before(series, dates, day):
    """Last close on or before `day` (dates sorted). None if nothing within 7 days."""
    lo, hi = 0, len(dates)
    while lo < hi:
        mid = (lo + hi) // 2
        if dates[mid] <= day:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return None, None
    d = dates[lo - 1]
    if (dt.date.fromisoformat(day) - dt.date.fromisoformat(d)).days > 7:
        return None, None
    return d, series[d]


def window_change(series, dates, start, end):
    """% change from last close before `start` to last close on/before `end`."""
    prev = (dt.date.fromisoformat(start) - dt.timedelta(days=1)).isoformat()
    d0, v0 = close_on_or_before(series, dates, prev)
    d1, v1 = close_on_or_before(series, dates, end)
    if v0 is None or v1 is None or d1 <= d0 or v0 == 0:
        return None
    return (v1 / v0 - 1) * 100


def shift_year(day, year):
    d = dt.date.fromisoformat(day)
    try:
        return d.replace(year=year)
    except ValueError:      # 29 Feb
        return d.replace(year=year, day=28)


def same_week_history(series, week_start, week_end, this_year, years=YEARS):
    dates = sorted(series)
    rows = []
    ws, we = dt.date.fromisoformat(week_start), dt.date.fromisoformat(week_end)
    for y in range(this_year - years, this_year):
        s = shift_year(week_start, y)
        e = s + (we - ws)
        c = window_change(series, dates, s.isoformat(), e.isoformat())
        if c is not None:
            rows.append({"year": y, "chg": round(c, 2)})
    return rows


def summarize(rows):
    if not rows:
        return None
    ch = [r["chg"] for r in rows]
    best = max(rows, key=lambda r: r["chg"])
    worst = min(rows, key=lambda r: r["chg"])
    return {"n": len(ch), "up": sum(1 for c in ch if c > 0), "down": sum(1 for c in ch if c < 0),
            "median": round(statistics.median(ch), 2), "best": best, "worst": worst}


# ---------------------------------------------------------------- text
def tr_num(v, nd=1):
    s = f"{abs(v):,.{nd}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("−" if v < 0 and round(abs(v), nd) != 0 else "") + s


def pct(v, nd=1):
    if round(v, nd) == 0:
        return "%" + tr_num(0.0, nd)
    return ("+" if v > 0 else "−") + "\u2060%" + tr_num(abs(v), nd)   # word joiner: no line break after sign


def tr_date(iso, year=True):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]}" + (f" {d.year}" if year else "")


def range_label(start, end):
    s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if s.month == e.month:
        return f"{s.day}–{e.day} {MONTHS[s.month - 1]}"
    return f"{s.day} {MONTHS[s.month - 1]} – {e.day} {MONTHS[e.month - 1]}"


def history_sentence(label, rng, s):
    if not s:
        return f"{label}: yeterli geçmiş veri yok."
    return (f"{label}: son {s['n']} yılın {rng} haftasında {s['up']} kez yükseldi, {s['down']} kez düştü; "
            f"ortanca {pct(s['median'])}. En güçlü {s['best']['year']} ({pct(s['best']['chg'])}), "
            f"en zayıf {s['worst']['year']} ({pct(s['worst']['chg'])}).")


def this_week_sentence(label, chg, rows, asof):
    if chg is None:
        return f"{label}: bu hafta için henüz kapanış yok."
    higher = sum(1 for r in rows if r["chg"] > chg)
    out = f"{label}: bu hafta şimdiye kadar {pct(chg)} ({tr_date(asof, False)} kapanışına göre)."
    n = len(rows)
    if n and higher == n:
        out += f" Son {n} yılın aynı haftalarının hepsinden zayıf."
    elif n and higher == 0:
        out += f" Son {n} yılın aynı haftalarının hepsinden güçlü."
    elif n:
        out += f" Son {n} yılın {higher} tanesinde aynı hafta daha yüksek kapanmıştı."
    return out


# ---------------------------------------------------------------- English (S13b): same facts, same numbers
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]
LABEL_EN = {"gram_altin": "Gold per gram (TRY)", "gram_gumus": "Silver per gram (TRY)", "dolar": "USD/TRY",
            "bist100_usd": "BIST 100 (in dollars)", "spy": "S&P 500 fund (SPY)",
            "qqq": "Nasdaq 100 tech fund (QQQ)", "btc": "Bitcoin (USD)"}
CAL_NAMES_EN = {"FOMC": "Fed rate decision (FOMC)", "CPI": "US inflation data (CPI)", "NFP": "US non-farm payrolls"}
DISCLAIMER_EN = "Past years' moves are historical information only; they say nothing about the future. Not investment advice."
METHOD_EN = ("Same calendar window every year: % change from the last close before the window to the last close "
             "inside it. Funds: price change excluding dividends.")


def en_pct(v, nd=1):
    if round(v, nd) == 0:
        return f"{0:.{nd}f}%"
    return ("+" if v > 0 else "−") + f"{abs(v):,.{nd}f}%"


def en_date(iso, year=True):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {MONTHS_EN[d.month - 1]}" + (f" {d.year}" if year else "")


def range_label_en(start, end):
    s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if s.month == e.month:
        return f"{s.day}–{e.day} {MONTHS_EN[s.month - 1]}"
    return f"{s.day} {MONTHS_EN[s.month - 1]} – {e.day} {MONTHS_EN[e.month - 1]}"


def history_sentence_en(label, rng, s):
    if not s:
        return f"{label}: not enough history."
    return (f"{label}: in the {rng} week of the last {s['n']} years it rose {s['up']} times and fell {s['down']} times; "
            f"median {en_pct(s['median'])}. Strongest {s['best']['year']} ({en_pct(s['best']['chg'])}), "
            f"weakest {s['worst']['year']} ({en_pct(s['worst']['chg'])}).")


def this_week_sentence_en(label, chg, rows, asof):
    if chg is None:
        return f"{label}: no close yet this week."
    higher = sum(1 for r in rows if r["chg"] > chg)
    out = f"{label}: {en_pct(chg)} so far this week (as of the {en_date(asof, False)} close)."
    n = len(rows)
    if n and higher == n:
        out += f" Weaker than the same week in each of the last {n} years."
    elif n and higher == 0:
        out += f" Stronger than the same week in each of the last {n} years."
    elif n:
        out += f" In {higher} of the last {n} years the same week closed higher."
    return out


# ---------------------------------------------------------------- editions
def week_bounds(today):
    mon = today - dt.timedelta(days=today.weekday())
    return mon.isoformat(), (mon + dt.timedelta(days=6)).isoformat()


def pick_entries(entries, week_start, week_end, week_no):
    ws, we = dt.date.fromisoformat(week_start), dt.date.fromisoformat(week_end)
    day, firsts = [], []
    for e in entries:
        if not e.get("url"):
            continue        # never publish an unsourced entry
        if e.get("precision") == "day":
            d = dt.date.fromisoformat(e["date"])
            for y in {ws.year, we.year}:
                try:
                    md = d.replace(year=y)
                except ValueError:
                    continue
                if ws <= md <= we:
                    day.append({**e, "md": md.isoformat()})
                    break
        elif e.get("precision") == "year":
            firsts.append(e)
    day.sort(key=lambda e: e["md"])
    out = [{"date": e["date"], "day_label": tr_date(e["md"], False), "year": int(e["date"][:4]),
            "topic": e.get("topic"), "title": e["title"], "text": e["text"],
            "day_label_en": en_date(e["md"], False), "topic_en": e.get("topic_en"),
            "title_en": e.get("title_en"), "text_en": e.get("text_en"),
            "source": e["source"], "url": e["url"]} for e in day]
    first = None
    if firsts:
        f = firsts[week_no % len(firsts)]
        first = {"year_label": f.get("year_label") or f["date"][:4], "title": f["title"], "text": f["text"],
                 "year_label_en": f.get("year_label_en") or f.get("year_label") or f["date"][:4],
                 "title_en": f.get("title_en"), "text_en": f.get("text_en"),
                 "source": f["source"], "url": f["url"]}
    return out, first


def calendar_items(notebook, week_start, week_end):
    try:
        cal = json.load(open(notebook, encoding="utf-8")).get("calendar") or {}
    except Exception:
        return []
    out = []
    for k, days in cal.items():
        for d in days:
            if week_start <= d <= week_end:
                out.append({"date": d, "day_label": tr_date(d, False), "name": CAL_NAMES.get(k, k),
                            "day_label_en": en_date(d, False), "name_en": CAL_NAMES_EN.get(k, k)})
    return sorted(out, key=lambda x: x["date"])


def load_extra(path, base):
    """Entries from the data-feed file; skipped if unsourced, malformed or a duplicate (same date + title)."""
    if not path or not os.path.exists(path):
        return []
    try:
        extra = json.load(open(path, encoding="utf-8")).get("entries", [])
    except Exception:
        return []
    seen = {(e.get("date"), e.get("title")) for e in base}
    out = []
    for e in extra:
        if not isinstance(e, dict) or not all(e.get(k) for k in ("date", "precision", "title", "text", "source", "url")):
            continue
        if not str(e["url"]).startswith("https://") or (e["date"], e["title"]) in seen:
            continue
        seen.add((e["date"], e["title"]))
        out.append(e)
    return out


def build(edition, today, raw_dir, notebook, tarihte, now_utc):
    ws, we = week_bounds(today)
    rng = range_label(ws, we)
    assets = []
    for aid, label, series in load_assets(raw_dir):
        rows = same_week_history(series, ws, we, today.year)
        item = {"id": aid, "label": label, "years": rows, "summary": summarize(rows)}
        item["sentence"] = history_sentence(label, rng, item["summary"])
        item["label_en"] = LABEL_EN.get(aid, label)
        item["sentence_en"] = history_sentence_en(item["label_en"], range_label_en(ws, we), item["summary"])
        if edition == "cuma":
            dates = sorted(series)
            chg = window_change(series, dates, ws, today.isoformat()) if series else None
            asof = close_on_or_before(series, dates, today.isoformat())[0] if series else None
            item["this_week"] = None if chg is None else round(chg, 2)
            item["this_week_asof"] = asof
            item["this_week_sentence"] = this_week_sentence(label, chg, rows, asof or today.isoformat())
            item["this_week_sentence_en"] = this_week_sentence_en(item["label_en"], chg, rows, asof or today.isoformat())
        assets.append(item)
    try:
        entries = json.load(open(tarihte, encoding="utf-8")).get("entries", [])
    except Exception:
        entries = []
    entries = entries + load_extra(TARIHTE_EXTRA, entries)
    week_no = today.isocalendar()[1]
    history, first = pick_entries(entries, ws, we, week_no)
    title = "Dünyada bu Pazartesi" if edition == "pazartesi" else "Dünyada bu Cuma"
    title_en = "The world this Monday" if edition == "pazartesi" else "The world this Friday"
    return {"schema": "phd.hafta/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
            "generated_at": now_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "attribution": ATTRIBUTION, "license": "Yalnızca görüntüleme (atıfla). Girdiler Yahoo Finance/OKX kişisel kullanım şartlı; CC BY 4.0 kapsamında değil. Ayrıntı: veri.html",
            "edition": edition, "title": title, "issue_date": today.isoformat(),
            "headline": f"{title} — {tr_date(today.isoformat())}",
            "week_start": ws, "week_end": we, "week_label": rng, "years": YEARS,
            "method": ("Her yıl aynı takvim aralığı: aralıktan önceki son kapanıştan aralıktaki son kapanışa "
                       "yüzde değişim. Fonlarda temettü hariç fiyat değişimi."),
            "assets": assets, "calendar": calendar_items(notebook, ws, we),
            "tarihte": history, "ilk": first, "disclaimer": DISCLAIMER,
            "title_en": title_en, "headline_en": f"{title_en} — {en_date(today.isoformat())}",
            "week_label_en": range_label_en(ws, we), "method_en": METHOD_EN, "disclaimer_en": DISCLAIMER_EN}


def should_build(today, site, force):
    if force in ("pazartesi", "cuma"):
        return force
    if today.weekday() == 0:
        return "pazartesi"
    if today.weekday() == 4:
        return "cuma"
    try:
        cur = json.load(open(os.path.join(site, "hafta.json"), encoding="utf-8"))
        if cur.get("week_start") == week_bounds(today)[0]:
            return None
    except Exception:
        pass
    return "cuma" if today.weekday() > 4 else "pazartesi"   # no edition for this week yet


def write_json(path, obj, overwrite=True):
    if not overwrite and os.path.exists(path):
        return False
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    return True


def main():
    now = dt.datetime.now(dt.timezone.utc)
    today = (now + dt.timedelta(hours=3)).date()       # Istanbul, no DST
    edition = should_build(today, SITE_OUT, os.environ.get("FORCE_EDITION", ""))
    if not edition:
        print("hafta: no edition today")
        return 0
    rec = build(edition, today, RAW_DIR, NOTEBOOK, TARIHTE, now)
    if not any(a["summary"] for a in rec["assets"]):
        print("hafta: no input data; nothing written")
        return 1
    os.makedirs(os.path.join(SITE_OUT, "hafta"), exist_ok=True)
    write_json(os.path.join(SITE_OUT, "hafta", f"{today.isoformat()}.json"), rec, overwrite=False)
    write_json(os.path.join(SITE_OUT, "hafta.json"), rec)
    print(f"hafta: {rec['headline']} ({len(rec['tarihte'])} tarih notu)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
