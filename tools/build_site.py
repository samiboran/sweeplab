"""Piyasa Hava Durumu — macro weather builder (rules v1, docs/MAKRO_KURALLAR_v1.md).

Reads data/derivs/notebook_daily.json (60-day window) and writes DERIVED data only
to SITE_OUT (default data/site, in the workflow feed/data/site on the data-feed branch):

  today.json               today's published record + pre-generated answers
  history.csv              append-only, one row per data date (never truncated)
  archive/YYYY-MM-DD.json  one record per data date (never rewritten)

Public output = level, per-rule 0/1 flags, rounded public-data values, % changes.
Licensed inputs (ICE BofA HY OAS, Nasdaq Composite, ICE DXY) leave this file only as a
0/1 flag and a direction word. Every number inside an answer sentence is inserted
here by a template; nothing is free-written.

On failure or stale inputs today.json says "güncellenmedi" (last good date kept)
and a short Telegram alert goes to Boran's chat (TELEGRAM_BOT_TOKEN/CHAT_ID).
"""
import csv
import datetime as dt
import json
import os
import sys
import traceback
import urllib.request

RULES_VERSION = "v1"
FREEZE_DATE = "2026-11-21"
SCHEMA_VERSION = 1
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
LICENSE = "CC BY 4.0 (yalnızca kamu kaynaklı türetilmiş alanlar)"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri, CC BY 4.0"
DISCLAIMER = "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır."
LOOKBACK = 20
MAX_WEEKDAY_AGE = 3      # daily inputs: older than 3 weekdays -> stale (weekends allowed)
MAX_WEEKLY_AGE = 10      # weekly Fed balance sheet (netliq): calendar days

NOTEBOOK = os.environ.get("NOTEBOOK", os.path.join(os.environ.get("OUT_DIR", "data/derivs"), "notebook_daily.json"))
SITE_OUT = os.environ.get("SITE_OUT", "data/site")

LEVELS = [(0, 2, "YESIL", "YEŞİL"), (3, 4, "SARI", "SARI"), (5, 9, "KIRMIZI", "KIRMIZI")]
GROUPS = {"L": "Likidite", "D": "Dolar", "K": "Kredi / risk", "N": "Nakde kaçış", "P": "Petrol"}
RULE_CODES = ["L1", "L2", "L3", "D1", "K1", "K2", "K3", "N1", "P1"]
# (path, as-of path, kind) — kind "weekly" uses the calendar allowance
CORE_INPUTS = {
    "stables": ("regime.stables_7d_pct", "regime.stables_asof", "daily"),
    "netliq": ("regime.netliq_musd", "regime.netliq_asof", "weekly"),
    "real10y": ("regime.real10y", "regime.real10y_asof", "daily"),
    "dxy": ("regime.dxy", "regime.dxy_asof", "daily"),
    "hy_oas": ("risk.hy_oas", "risk.hy_asof", "daily"),
    "vix": ("risk.vix", "risk.vix_asof", "daily"),
    "ndx": ("risk.ndx", "risk.ndx_asof", "daily"),
    "gold": ("macro.gold", "macro.gold_asof", "daily"),
    "wti": ("macro.wti", "macro.wti_asof", "daily"),
}
HISTORY_FIELDS = ["date", "rules_version", "mode", "raw_score", "raw_level", "level", "level_held",
                  *RULE_CODES, "p1_label", "generated_at"]
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
          "Eylül", "Ekim", "Kasım", "Aralık"]


# ---------------------------------------------------------------- helpers
def get(row, path):
    cur = row
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def pct(a, b):
    if a is None or b in (None, 0):
        return None
    return (a / b - 1) * 100


def diff(a, b):
    if a is None or b is None:
        return None
    return a - b


def level_of(score):
    for lo, hi, code, _ in LEVELS:
        if lo <= score <= hi:
            return code
    return "KIRMIZI"


def level_word(code):
    return {c: w for _, _, c, w in LEVELS}[code]


def tr_num(v, nd=1):
    """Turkish number format: 1.234,5"""
    s = f"{abs(v):,.{nd}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("−" if v < 0 and round(abs(v), nd) != 0 else "") + s


def tr_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def direction(v, eps=0.0):
    if v is None:
        return "veri yok"
    if v > eps:
        return "yükseldi"
    if v < -eps:
        return "düştü"
    return "yatay"


def r(v, nd):
    return None if v is None else round(v, nd)


def weekday_age(asof, today):
    """Weekdays in (asof, today] — weekends do not count."""
    a, t = dt.date.fromisoformat(asof), dt.date.fromisoformat(today)
    n, d = 0, a
    while d < t:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


# ---------------------------------------------------------------- rules v1
def score_row(rows, i):
    """Score rows[i] against rows[i-20] (or the oldest row). Returns a dict."""
    cur, base = rows[i], rows[max(0, i - LOOKBACK)]
    g = lambda p: get(cur, p)
    b = lambda p: get(base, p)

    stables = g("regime.stables_7d_pct")
    netliq_chg = diff(g("regime.netliq_musd"), b("regime.netliq_musd"))
    netliq_pct = pct(g("regime.netliq_musd"), b("regime.netliq_musd"))
    real_chg = diff(g("regime.real10y"), b("regime.real10y"))
    dxy_pct = pct(g("regime.dxy"), b("regime.dxy"))
    hy_chg = diff(g("risk.hy_oas"), b("risk.hy_oas"))
    vix = g("risk.vix")
    ndx_pct = pct(g("risk.ndx"), b("risk.ndx"))
    gold_pct = pct(g("macro.gold"), b("macro.gold"))
    wti_pct = pct(g("macro.wti"), b("macro.wti"))

    def flag(cond, *inputs):
        if any(x is None for x in inputs):
            return None
        return 1 if cond() else 0

    p1_label = None
    if wti_pct is not None and wti_pct >= 10:
        p1_label = "enflasyon dürtüsü"
    elif wti_pct is not None and hy_chg is not None and wti_pct <= -15 and hy_chg > 0:
        p1_label = "talep zayıflığı"

    flags = {
        "L1": flag(lambda: stables < 0, stables),
        "L2": flag(lambda: netliq_chg < 0, netliq_chg),
        "L3": flag(lambda: real_chg >= 0.15 - 1e-9, real_chg),
        "D1": flag(lambda: dxy_pct >= 1.0, dxy_pct),
        "K1": flag(lambda: hy_chg >= 0.25 - 1e-9, hy_chg),
        "K2": flag(lambda: vix >= 18, vix),
        "K3": flag(lambda: ndx_pct <= -3.0, ndx_pct),
        "N1": flag(lambda: gold_pct <= -3.0 and dxy_pct > 0, gold_pct, dxy_pct),
        "P1": (None if wti_pct is None else (1 if p1_label else 0)),
    }
    score = sum(v or 0 for v in flags.values())
    # Public values: rounded public-data values / % changes; licensed -> direction word only.
    values = {
        "stables_7d_pct": r(stables, 1),
        "netliq_20g_pct": r(netliq_pct, 2),
        "real10y": r(g("regime.real10y"), 2),
        "real10y_20g_bp": None if real_chg is None else round(real_chg * 100),
        "dxy_20g_yon": direction(dxy_pct, 0.05),
        "hy_oas_20g_yon": {"yükseldi": "açıldı", "düştü": "daraldı"}.get(direction(hy_chg, 0.005), direction(hy_chg, 0.005)),
        "vix": r(vix, 1),
        "ndx_20g_yon": direction(ndx_pct, 0.05),
        "gold_20g_pct": r(gold_pct, 1),
        "wti_20g_pct": r(wti_pct, 1),
    }
    return {"date": cur["date"], "base_date": base["date"], "flags": flags, "raw_score": score,
            "raw_level": level_of(score), "p1_label": p1_label, "values": values,
            "trend": {c: cur.get("regime", {}).get(f"trend_{c}") for c in ("btc", "eth")}}


def publish_level(prev_published, prev_raw_level, raw_level):
    """Noise filter: change only when today's and yesterday's raw levels agree on a new level."""
    if prev_published is None:
        return raw_level, False
    if raw_level != prev_published and raw_level == prev_raw_level:
        return raw_level, False
    return prev_published, raw_level != prev_published


# ---------------------------------------------------------------- sentences
def rule_sentence(code, s):
    v, f = s["values"], s["flags"][code]
    if f is None:
        return "Bu kural için bugün veri yok; puan verilmedi."
    if code == "L1":
        x = v["stables_7d_pct"]
        return f"Stablecoin arzı son 7 günde %{tr_num(abs(x))} {'azaldı' if x < 0 else 'arttı' if x > 0 else 'değişmedi'}."
    if code == "L2":
        x = v["netliq_20g_pct"]
        return f"Fed net likiditesi 20 günde %{tr_num(abs(x), 2)} {'azaldı' if x < 0 else 'arttı' if x > 0 else 'değişmedi'}."
    if code == "L3":
        x = v["real10y_20g_bp"]
        word = "yükseldi" if x > 0 else "düştü" if x < 0 else "değişmedi"
        return f"10 yıllık reel faiz %{tr_num(v['real10y'], 2)}; 20 günde {abs(x)} baz puan {word}."
    if code == "D1":
        return f"Dolar endeksi 20 günde {v['dxy_20g_yon']}" + ("; eşik aşıldı." if f else "; eşik aşılmadı.")
    if code == "K1":
        return f"Yüksek getirili tahvil risk primi 20 günde {v['hy_oas_20g_yon']}" + ("; eşik aşıldı." if f else "; eşik aşılmadı.")
    if code == "K2":
        return f"VIX oynaklık endeksi {tr_num(v['vix'])}" + (" (18 ve üzeri)." if f else " (18'in altında).")
    if code == "K3":
        return f"Nasdaq Bileşik endeksi 20 günde {v['ndx_20g_yon']}" + ("; eşik aşıldı." if f else "; eşik aşılmadı.")
    if code == "N1":
        x = v["gold_20g_pct"]
        g = f"Altın 20 günde %{tr_num(abs(x))} {'geriledi' if x < 0 else 'yükseldi' if x > 0 else 'değişmedi'}"
        return g + f", dolar endeksi {v['dxy_20g_yon']}" + (" — nakde kaçış işareti." if f else ".")
    if code == "P1":
        x = v["wti_20g_pct"]
        t = f"Ham petrol (WTI) 20 günde %{tr_num(abs(x))} {'geriledi' if x < 0 else 'yükseldi' if x > 0 else 'değişmedi'}"
        return t + (f" — {s['p1_label']} işareti." if f else ".")
    raise KeyError(code)


RULE_TITLES = {
    "L1": "Stablecoin arzı", "L2": "Fed net likiditesi", "L3": "Reel faiz",
    "D1": "Dolar endeksi", "K1": "Kredi risk primi", "K2": "Oynaklık (VIX)",
    "K3": "Nasdaq Bileşik", "N1": "Altın ve dolar", "P1": "Petrol",
}


def trend_sentence(name, t):
    if not t or t.get("close") is None or t.get("dist200_pct") is None:
        return f"{name} için trend verisi yok."
    d200, d50 = t["dist200_pct"], t.get("dist50_pct")
    rel = lambda d: f"%{tr_num(abs(d))} {'altında' if d < 0 else 'üstünde'}"
    out = f"{name} günlük kapanışı {tr_num(t['close'], 0 if t['close'] >= 1000 else 2)} $; 200 günlük ortalamanın {rel(d200)}"
    if d50 is not None:
        out += f", 50 günlük ortalamanın {rel(d50)}"
    return out + "."


def answers(rec, prev):
    lvl, sc = rec["level_word"], rec["raw_score"]
    a1 = [f"{tr_date(rec['publish_date'])} itibarıyla makro hava: {lvl}.",
          f"Dokuz kuraldan {sc} tanesi işaret veriyor (ham skor {sc}/9)."]
    if rec["level_held"]:
        a1.append(rec["held_note"])
    a1.append(f"Veriler {tr_date(rec['data_date'])} kapanışına ait.")
    on = [x for x in rec["rules"] if x["flag"] == 1]
    a2 = [x["sentence"] for x in on] or ["Bugün hiçbir kural işaret vermiyor."]
    a3 = []
    if prev:
        pf = {k: prev.get(k) for k in RULE_CODES}
        for x in rec["rules"]:
            old = pf.get(x["code"])
            if old is not None and x["flag"] is not None and int(old) != x["flag"]:
                a3.append(f"{x['title']}: {'işaret vermeye başladı' if x['flag'] else 'işareti söndü'}.")
        ps = int(prev["raw_score"])
        a3.insert(0, f"Ham skor {ps} → {sc}." if ps != sc else f"Ham skor değişmedi ({sc}).")
        if prev.get("level") != rec["level"]:
            a3.append(f"Yayımlanan seviye {level_word(prev['level'])} → {lvl}.")
    else:
        a3 = ["Karşılaştırma için önceki gün kaydı yok."]
    a4 = [trend_sentence("BTC", rec["trend"].get("btc")), trend_sentence("ETH", rec["trend"].get("eth"))]
    a5 = ["Skor, likidite, dolar, kredi/risk, nakde kaçış ve petrol başlıklarındaki dokuz kuraldan oluşur; her kural 1 puan.",
          "0–2 YEŞİL, 3–4 SARI, 5 ve üzeri KIRMIZI. Seviye, ikinci gün onayı olmadan değişmez.",
          "Kurallar sabittir ve sürümlenir; yayımlanan skorlar sonradan değiştirilmez."]
    return [
        {"id": "hava", "q": "Bugün makro hava nasıl?", "a": a1},
        {"id": "isaretler", "q": "Hangi kurallar işaret veriyor?", "a": a2},
        {"id": "degisim", "q": "Dünden bu yana ne değişti?", "a": a3},
        {"id": "kripto", "q": "BTC ve ETH ortalamalara göre nerede?", "a": a4},
        {"id": "yontem", "q": "Bu ölçüm nasıl yapılıyor?", "a": a5, "link": "yontem.html"},
    ]


# ---------------------------------------------------------------- records / IO
def provenance(generated_at):
    return {"source": SOURCE, "site_url": SITE_URL, "rules_version": RULES_VERSION,
            "generated_at": generated_at, "license": LICENSE, "attribution": ATTRIBUTION,
            "schema_version": SCHEMA_VERSION}


def build_record(s, level, held, mode, generated_at, publish_date, inputs_asof):
    rec = {**provenance(generated_at), "status": "güncel", "mode": mode,
           "data_date": s["date"], "publish_date": publish_date, "compare_date": s["base_date"],
           "last_good_date": s["date"],
           "level": level, "level_word": level_word(level), "raw_score": s["raw_score"],
           "max_score": 9, "raw_level": s["raw_level"], "level_held": held,
           "held_note": (f"Ham skor {level_word(s['raw_level'])} seviyesine işaret ediyor; "
                         f"değişim için ikinci gün onayı bekleniyor.") if held else None,
           "headline": f"{tr_date(publish_date)} — Makro hava: {level_word(level)}",
           "groups": {}, "rules": [], "values": s["values"], "trend": s["trend"],
           "inputs_asof": inputs_asof, "disclaimer": DISCLAIMER}
    for code in RULE_CODES:
        f = s["flags"][code]
        rec["rules"].append({"code": code, "group": GROUPS[code[0]], "title": RULE_TITLES[code],
                             "flag": f, "sentence": rule_sentence(code, s),
                             **({"label": s["p1_label"]} if code == "P1" and s["p1_label"] else {})})
        grp = rec["groups"].setdefault(GROUPS[code[0]], {"points": 0, "max": 0})
        grp["points"] += f or 0
        grp["max"] += 1
    return rec


def history_row(rec):
    row = {"date": rec["data_date"], "rules_version": rec["rules_version"], "mode": rec["mode"],
           "raw_score": rec["raw_score"], "raw_level": rec["raw_level"], "level": rec["level"],
           "level_held": int(rec["level_held"]), "p1_label": next((x.get("label", "") for x in rec["rules"] if x["code"] == "P1"), ""),
           "generated_at": rec["generated_at"]}
    for x in rec["rules"]:
        row[x["code"]] = "" if x["flag"] is None else x["flag"]
    return row


def read_history(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_history(path, rows):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HISTORY_FIELDS, lineterminator="\n")
        if new:
            w.writeheader()
        for row in rows:
            w.writerow(row)


def write_json(path, obj, overwrite=True):
    if not overwrite and os.path.exists(path):
        return False
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return True


def inputs_asof(row):
    return {k: get(row, a) for k, (_, a, _) in CORE_INPUTS.items()}


def business_day(d):
    """The row's own date, or the Friday before for a weekend row."""
    x = dt.date.fromisoformat(d)
    while x.weekday() > 4:
        x -= dt.timedelta(days=1)
    return x.isoformat()


def settled(rows, i):
    """True when rows[i]'s daily inputs are final for its date: each daily core input is
    from the row's own business day, or a LATER row already carries a newer value for it
    (the source had nothing for that day, e.g. a US holiday).
    The morning build's newest row usually still carries the previous day's US data
    (FRED publishes VIX, real yield, HY OAS a day later); scoring it would mix days."""
    row = rows[i]
    a = inputs_asof(row)
    for k, (_, ap, kind) in CORE_INPUTS.items():
        if kind == "weekly":
            continue
        d = a.get(k)
        if not d:
            return False
        need = row["date"] if k == "stables" else business_day(row["date"])
        if str(d)[:10] >= need:
            continue
        later = any(str(get(r, ap) or "")[:10] > row["date"] for r in rows[i + 1:])
        if not later:
            return False
    return True


def settled_rows(rows):
    """rows up to and including the newest settled row ([] if none)."""
    for i in range(len(rows) - 1, -1, -1):
        if settled(rows, i):
            return rows[:i + 1]
    return []


def stale_inputs(asof, today):
    out = []
    for k, (_, _, kind) in CORE_INPUTS.items():
        d = asof.get(k)
        if not d:
            out.append(k)
            continue
        if kind == "weekly":
            if (dt.date.fromisoformat(today) - dt.date.fromisoformat(d)).days > MAX_WEEKLY_AGE:
                out.append(k)
        elif weekday_age(d, today) > MAX_WEEKDAY_AGE:
            out.append(k)
    return out


def mark_stale(site, reason, generated_at, publish_date):
    """Keep the last good record, flip status to 'güncellenmedi'."""
    path = os.path.join(site, "today.json")
    try:
        prev = json.load(open(path, encoding="utf-8"))
    except Exception:
        prev = {**provenance(generated_at), "last_good_date": None, "mode": None, "level": None}
    prev.update({"status": "güncellenmedi", "stale_reason": reason, "checked_at": generated_at,
                 "check_date": publish_date})
    os.makedirs(site, exist_ok=True)
    write_json(path, prev)
    return prev


def alert(text):
    if os.environ.get("SEND_TELEGRAM", "1") != "1":
        print("alert (not sent):", text)
        return
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram secrets missing; alert not sent.")
        return
    try:
        body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        print("alert sent")
    except Exception as e:  # never print the URL (contains the token)
        print("alert failed:", type(e).__name__)


def build(notebook, site, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    generated_at = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    publish_date = (now + dt.timedelta(hours=3)).date().isoformat()   # Istanbul, no DST
    rows = sorted(json.load(open(notebook, encoding="utf-8"))["rows"], key=lambda x: x["date"])
    if not rows:
        raise ValueError("notebook has no rows")
    rows = settled_rows(rows)            # score only days whose inputs are complete
    if not rows:
        raise ValueError("notebook has no settled row")
    os.makedirs(os.path.join(site, "archive"), exist_ok=True)
    hpath = os.path.join(site, "history.csv")
    hist = read_history(hpath)
    last_date = hist[-1]["date"] if hist else None

    asof = inputs_asof(rows[-1])
    stale = stale_inputs(asof, publish_date)
    if stale:
        mark_stale(site, "eski girdi: " + ", ".join(stale), generated_at, publish_date)
        return {"status": "stale", "stale": stale}

    prev_pub = hist[-1]["level"] if hist else None
    prev_raw = hist[-1]["raw_level"] if hist else None
    new_rows, rec, prev_hist = [], None, (hist[-1] if hist else None)
    for i, row in enumerate(rows):
        if last_date and row["date"] <= last_date:
            continue
        s = score_row(rows, i)
        level, held = publish_level(prev_pub, prev_raw, s["raw_level"])
        is_latest = i == len(rows) - 1
        mode = "live" if (hist and is_latest and s["date"] >= FREEZE_DATE) else "retro"
        rec = build_record(s, level, held, mode, generated_at,
                           publish_date if is_latest else s["date"], inputs_asof(row))
        hrow = history_row(rec)
        rec["answers"] = answers(rec, prev_hist)
        write_json(os.path.join(site, "archive", f"{s['date']}.json"), rec, overwrite=False)
        new_rows.append(hrow)
        prev_pub, prev_raw, prev_hist = level, s["raw_level"], hrow
    if new_rows:
        append_history(hpath, new_rows)
    if rec is None:   # no new data date: keep today's record, note the check
        tpath = os.path.join(site, "today.json")
        if os.path.exists(tpath):
            t = json.load(open(tpath, encoding="utf-8"))
            if t.get("data_date") == rows[-1]["date"] and t.get("status") == "güncel":
                t["checked_at"] = generated_at
                write_json(tpath, t)
                return {"status": "unchanged", "date": t["data_date"]}
        # today.json missing/stale but history has the date: rebuild from archive
        apath = os.path.join(site, "archive", f"{rows[-1]['date']}.json")
        rec = json.load(open(apath, encoding="utf-8"))
    write_json(os.path.join(site, "today.json"), rec)
    return {"status": "ok", "date": rec["data_date"], "level": rec["level"], "raw_score": rec["raw_score"],
            "appended": len(new_rows), "mode": rec["mode"]}


def main():
    now = dt.datetime.now(dt.timezone.utc)
    try:
        res = build(NOTEBOOK, SITE_OUT, now)
    except Exception as e:
        traceback.print_exc()
        ga = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        last = mark_stale(SITE_OUT, f"derleme hatası: {type(e).__name__}", ga,
                          (now + dt.timedelta(hours=3)).date().isoformat())
        alert(f"Piyasa Hava Durumu: site derlemesi başarısız ({type(e).__name__}). "
              f"Sayfa 'güncellenmedi' gösteriyor; son iyi tarih {last.get('last_good_date') or '—'}.")
        return 1
    print(json.dumps(res, ensure_ascii=False))
    if res["status"] == "stale":
        alert(f"Piyasa Hava Durumu: güncellenmedi — eski girdi: {', '.join(res['stale'])}. "
              "Son iyi kayıt sayfada duruyor.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
