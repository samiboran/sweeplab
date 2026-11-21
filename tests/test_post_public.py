"""Tests for tools/post_public.py (public Telegram channel, roadmap S7)."""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import post_public as pp  # noqa: E402

FIELDS = ["date", "rules_version", "mode", "raw_score", "raw_level", "level", "level_held",
          *pp.RULE_CODES, "p1_label", "generated_at"]
TODAY = {"status": "güncel", "data_date": "2026-11-24",
         "rules": [{"code": "K2", "title": "Oynaklık (VIX)"}, {"code": "P1", "title": "Petrol"}]}
BANNED = ["al ", "sat ", "fırsat", "ucuz", "hedef", "kaçırma", "🚀"]


def row(date, level, score, mode="live", **flags):
    r = {k: "0" for k in FIELDS}
    r.update(date=date, rules_version="v1", mode=mode, raw_score=str(score), raw_level=level, level=level)
    r.update({k: str(v) for k, v in flags.items()})
    return r


def test_level_change_live_posts_changed_rules():
    hist = [row("2026-11-23", "KIRMIZI", 5, K2=1, P1=1), row("2026-11-24", "SARI", 3, P1=1)]
    m = pp.level_change_message(hist, TODAY, "https://x/")
    assert "Makro hava: SARI (önceki: KIRMIZI)" in m
    assert "İşareti kalkan kurallar: Oynaklık (VIX)" in m
    assert m.endswith(pp.DISCLAIMER) and "Yatırım tavsiyesi değildir." in m
    assert not any(b in m.lower() for b in BANNED)


def test_no_post_for_retro_same_level_or_stale():
    retro = [row("2026-11-23", "KIRMIZI", 5), row("2026-11-24", "SARI", 3, mode="retro")]
    assert pp.level_change_message(retro, TODAY) is None
    same = [row("2026-11-23", "SARI", 4), row("2026-11-24", "SARI", 3)]
    assert pp.level_change_message(same, TODAY) is None
    live = [row("2026-11-23", "KIRMIZI", 5), row("2026-11-24", "SARI", 3)]
    assert pp.level_change_message(live, dict(TODAY, status="güncellenmedi")) is None


def test_weekly_only_on_istanbul_sunday():
    hist = [row(f"2026-11-{d}", "KIRMIZI" if d < 26 else "SARI", 5 if d < 26 else 3) for d in range(20, 28)]
    today = dict(TODAY, data_date="2026-11-27")
    sat = dt.datetime(2026, 11, 28, 6, 0, tzinfo=dt.timezone.utc)
    sun = dt.datetime(2026, 11, 29, 6, 0, tzinfo=dt.timezone.utc)
    assert pp.weekly_message(hist, today, sat) is None
    m = pp.weekly_message(hist, today, sun, "https://x/")
    assert "haftalık özet" in m and "SARI 2 gün" in m and "KIRMIZI 3 gün" in m
    assert "Seviye hafta başında KIRMIZI idi." in m and m.endswith(pp.DISCLAIMER)


def test_run_skips_without_channel_and_dedupes(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    hist = [row("2026-11-23", "KIRMIZI", 5), row("2026-11-24", "SARI", 3)]
    with open(site / "history.csv", "w", encoding="utf-8", newline="") as f:
        import csv
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(hist)
    (site / "today.json").write_text(json.dumps(TODAY), encoding="utf-8")
    monkeypatch.setattr(pp, "SITE_OUT", str(site))
    monkeypatch.setattr(pp, "STATE", str(tmp_path / "state.json"))
    monkeypatch.delenv("TELEGRAM_PUBLIC_CHANNEL_ID", raising=False)
    assert pp.run() == "skipped"
    monkeypatch.setenv("TELEGRAM_PUBLIC_CHANNEL_ID", "@kanal")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("SEND_TELEGRAM", "1")
    sent = []
    now = dt.datetime(2026, 11, 25, 6, 0, tzinfo=dt.timezone.utc)   # Wednesday
    assert pp.run(now, sender=lambda t, c, x: sent.append(x)) == "sent"
    assert len(sent) == 1
    assert pp.run(now, sender=lambda t, c, x: sent.append(x)) == "none"   # no double post
    assert len(sent) == 1
