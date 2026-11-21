"""Piyasa Hava Durumu — public Telegram channel posts (roadmap S7).

Optional: runs only if TELEGRAM_PUBLIC_CHANNEL_ID is set (same bot as the daily brief,
TELEGRAM_BOT_TOKEN). Posts to the PUBLIC channel only

  (a) when the PUBLISHED level changes (last history.csv row vs the one before,
      live rows only — retro back-fill never posts), and
  (b) a short weekly summary on Sunday (Istanbul time).

Message = level, changed rules, link, disclaimer. Every number comes from the derived
site data (data/site/history.csv + today.json); licensed inputs never appear (only
the rule titles). A small state file (STATE, private side: data/derivs/) prevents
double posts when the workflow runs twice in a day. The token is never printed.
"""
import csv
import datetime as dt
import json
import os
import sys
import urllib.request

SITE_OUT = os.environ.get("SITE_OUT", "data/site")
STATE = os.environ.get("PUBLIC_STATE", os.path.join(os.environ.get("OUT_DIR", "data/derivs"),
                                                    "public_channel_state.json"))
SITE_URL = os.environ.get("SITE_BASE") or "https://samiboran.github.io/sweeplab/piyasa/"
DISCLAIMER = "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır."
RULE_CODES = ["L1", "L2", "L3", "D1", "K1", "K2", "K3", "N1", "P1"]
LEVEL_WORD = {"YESIL": "YEŞİL", "SARI": "SARI", "KIRMIZI": "KIRMIZI"}
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
          "Eylül", "Ekim", "Kasım", "Aralık"]


def tr_date(iso):
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def read_history(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def titles(today):
    t = {c: c for c in RULE_CODES}
    for r in today.get("rules") or []:
        if r.get("code") in t and r.get("title"):
            t[r["code"]] = r["title"]
    return t


def changed_rules(prev, cur, tt):
    on, off = [], []
    for c in RULE_CODES:
        a, b = str(prev.get(c, "0")), str(cur.get(c, "0"))
        if a != b:
            (on if b == "1" else off).append(tt[c])
    return on, off


def level_change_message(hist, today, site_url=SITE_URL):
    """Return the post text if the published level changed on the last live row, else None."""
    if len(hist) < 2:
        return None
    cur, prev = hist[-1], hist[-2]
    if cur.get("mode") != "live" or cur["level"] == prev["level"]:
        return None
    if today.get("status") != "güncel" or today.get("data_date") != cur["date"]:
        return None
    tt = titles(today)
    on, off = changed_rules(prev, cur, tt)
    lines = [f"Piyasa Hava Durumu — {tr_date(cur['date'])}",
             f"Makro hava: {LEVEL_WORD[cur['level']]} (önceki: {LEVEL_WORD[prev['level']]})",
             f"Puan: {cur['raw_score']}/9"]
    if on:
        lines.append("İşaret veren kurallar (yeni): " + ", ".join(on))
    if off:
        lines.append("İşareti kalkan kurallar: " + ", ".join(off))
    lines += ["", site_url, DISCLAIMER]
    return "\n".join(lines)


def weekly_message(hist, today, now, site_url=SITE_URL):
    """Sunday summary over the last 7 calendar days of history (Istanbul date)."""
    day = (now + dt.timedelta(hours=3)).date()
    if day.weekday() != 6 or not hist or today.get("status") != "güncel":
        return None
    start = (day - dt.timedelta(days=7)).isoformat()
    week = [h for h in hist if h["date"] > start]
    if not week:
        return None
    cur = hist[-1]
    before = [h for h in hist if h["date"] <= start]
    base = before[-1] if before else week[0]
    counts = {}
    for h in week:
        counts[h["level"]] = counts.get(h["level"], 0) + 1
    tt = titles(today)
    on, off = changed_rules(base, cur, tt)
    lines = [f"Piyasa Hava Durumu — haftalık özet ({tr_date(week[0]['date'])} – {tr_date(cur['date'])})",
             f"Son kayıt: {LEVEL_WORD[cur['level']]}, puan {cur['raw_score']}/9",
             "Hafta içindeki günler: " + ", ".join(f"{LEVEL_WORD[k]} {v} gün"
                                                    for k, v in sorted(counts.items(), key=lambda x: -x[1]))]
    if base["level"] != cur["level"]:
        lines.append(f"Seviye hafta başında {LEVEL_WORD[base['level']]} idi.")
    else:
        lines.append("Seviye hafta boyunca değişmedi." if len(counts) == 1 else
                     f"Seviye hafta başındaki gibi {LEVEL_WORD[cur['level']]}.")
    if on:
        lines.append("Hafta içinde işaret vermeye başlayan kurallar: " + ", ".join(on))
    if off:
        lines.append("Hafta içinde işareti kalkan kurallar: " + ", ".join(off))
    lines += ["", site_url, DISCLAIMER]
    return "\n".join(lines)


def send(token, chat, text):
    body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": False}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).read()


def run(now=None, sender=send):
    now = now or dt.datetime.now(dt.timezone.utc)
    chat = os.environ.get("TELEGRAM_PUBLIC_CHANNEL_ID")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not chat:
        print("public channel: TELEGRAM_PUBLIC_CHANNEL_ID not set; skipped")
        return "skipped"
    hist = read_history(os.path.join(SITE_OUT, "history.csv"))
    today = load_json(os.path.join(SITE_OUT, "today.json"), {})
    state = load_json(STATE, {})
    istanbul = (now + dt.timedelta(hours=3)).date().isoformat()
    posts = []
    m = level_change_message(hist, today)
    if m and state.get("last_level_post") != hist[-1]["date"]:
        posts.append(("last_level_post", hist[-1]["date"], m))
    w = weekly_message(hist, today, now)
    if w and state.get("last_weekly_post") != istanbul:
        posts.append(("last_weekly_post", istanbul, w))
    if not posts:
        print("public channel: nothing to post")
        return "none"
    if os.environ.get("SEND_TELEGRAM", "1") != "1" or not token:
        for _, _, text in posts:
            print("public post (not sent):\n" + text)
        return "dry"
    for key, val, text in posts:
        try:
            sender(token, chat, text)
            state[key] = val
            print("public post sent:", key)
        except Exception as e:  # never print the URL (contains the token)
            print("public post failed:", type(e).__name__)
    os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    return "sent"


if __name__ == "__main__":
    run()
    sys.exit(0)
