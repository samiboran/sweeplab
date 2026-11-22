"""Piyasa Hava Durumu — machine-readable data catalogue (S10).

Writes data/site/index.json: every public endpoint under data/site/ with its stable path,
schema id + version, update time, license class and whether it exists today. Paths are
relative to the data root so they stay the same when the site moves to its final host
(GitHub raw today, <site>/data/site/ later). Human docs: piyasa/veri.html.
"""
import datetime as dt, json, os

FEED = os.environ.get("FEED_DIR", "data")
SITE_OUT = os.environ.get("SITE_OUT", os.path.join(FEED, "site"))
SOURCE = "Piyasa Hava Durumu"
SITE_URL = "https://samiboran.github.io/sweeplab/piyasa/"
RAW_BASE = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/"
ATTRIBUTION = "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri, CC BY 4.0"
CC = "CC BY 4.0"
VIEW = "yalnızca görüntüleme"
MIXED = "karışık (alan düzeyinde; veri.html)"

ENDPOINTS = [
    # path, schema, version, update (UTC), license, description
    ("today.json", "phd.today/1", 1, "her gün ~06:00", MIXED,
     "Bugünün makro havası: seviye, ham skor, 9 kuralın 0/1 işareti, yuvarlanmış kamu verisi değerleri, tazelik durumu."),
    ("history.csv", "phd.history/1", 1, "her gün ~06:00", CC,
     "Her günün seviyesi, ham skoru ve 9 kural işareti; yalnız ekleme yapılır (retro/live)."),
    ("archive/{YYYY-MM-DD}.json", "phd.today/1", 1, "her gün ~06:00", MIXED,
     "Geçmiş bir günün yayımlandığı haliyle kaydı; yeniden yazılmaz (belgelenmiş düzeltme hariç)."),
    ("sicil.json", "phd.sicil/1", 1, "her gün ~06:00", CC,
     "KIRMIZI geçişlerinin sonucu: teyit / yanlış alarm / kaçırılan düşüş (yalnız kelime)."),
    ("tl.json", "phd.tl/1", 1, "her gün ~06:00", VIEW,
     "Gram altın, gram gümüş, dolar/TL, BIST 100 (dolar bazında): değişimler ve küçük grafik serisi."),
    ("konum.json", "phd.konum/1", 1, "her gün ~06:00", VIEW,
     "Sabit evrende 20/50/200 günlük ortalamaya göre konum (0/1) ve 200 güne yüzde uzaklık."),
    ("charts.json", "phd.charts/1", 1, "her gün ~06:00", MIXED,
     "BTC/ETH günlük kapanış + 50/200 gün ortalaması (görüntüleme) ve makro skor geçmişi (CC BY 4.0)."),
    ("hafta.json", "phd.hafta/1", 1, "pazartesi ve cuma ~06:00", VIEW,
     "Dünyada bu Pazartesi / Cuma: aynı haftanın son 10 yıldaki seyri, takvim, kaynaklı tarih notları."),
    ("hafta/{YYYY-MM-DD}.json", "phd.hafta/1", 1, "pazartesi ve cuma ~06:00", VIEW, "Geçmiş haftalık baskılar."),
    ("og.png", None, None, "her gün ~06:00", CC, "Günün başlık kartı (1200×630)."),
    ("dunya.json", "phd.dunya/1", 1, "her gün ~06:00", VIEW,
     "Bölge endeks/fonları ve büyük şirketler (değişim + ortalamalara göre yer), emtialar, referans metaller, günün başlıkları (yalnız başlık + kaynak + saat + bağlantı)."),
    ("movers.json", "phd.movers/1", 1, "planlı (S10c)", VIEW, "Günün hareketlileri ve kural tabanlı anomaliler."),
    ("movers_news.json", "phd.movers_news/1", 1, "planlı (S10c)", VIEW,
     "Hareketlilere eşleştirilen haber başlıkları (yalnız başlık + kaynak + saat + bağlantı)."),
]


def build(site_dir, now=None):
    now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = []
    for path, schema, ver, upd, lic, desc in ENDPOINTS:
        if "{" in path:
            sub = os.path.join(site_dir, path.split("/")[0])
            files = sorted(f for f in os.listdir(sub) if f.endswith(".json")) if os.path.isdir(sub) else []
            exists, extra = bool(files), {"first": files[0][:-5] if files else None, "last": files[-1][:-5] if files else None,
                                          "count": len(files)}
        else:
            exists, extra = os.path.exists(os.path.join(site_dir, path)), {}
        row = {"path": path, "schema": schema, "schema_version": ver, "update_utc": upd, "license": lic,
               "description": desc, "exists": exists}
        row.update(extra)
        rows.append(row)
    return {"schema": "phd.index/1", "schema_version": 1, "source": SOURCE, "site_url": SITE_URL,
            "docs": SITE_URL + "veri.html", "generated_at": now, "attribution": ATTRIBUTION,
            "license": MIXED, "base_url_now": RAW_BASE,
            "base_url_note": "Yollar data/site/ köküne göredir ve sabittir; son barındırıcıda <site>/data/site/ altında aynı kalır.",
            "stability": "Bir şemada alan eklemek sürümü değiştirmez; alan kaldırmak ya da anlamını değiştirmek yeni sürüm (…/2) demektir ve eski sürüm en az 90 gün yan yana yayımlanır.",
            "disclaimer": "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır.",
            "endpoints": rows}


def main():
    rec = build(SITE_OUT)
    os.makedirs(SITE_OUT, exist_ok=True)
    path = os.path.join(SITE_OUT, "index.json")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)
    print("index.json:", sum(r["exists"] for r in rec["endpoints"]), "of", len(rec["endpoints"]), "endpoints present")


if __name__ == "__main__":
    main()
