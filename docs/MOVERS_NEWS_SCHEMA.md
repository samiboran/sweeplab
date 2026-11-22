# movers_news.json — şema (phd.movers_news/1)

Günün hareketlileri sayfasındaki (`piyasa/hareket.html`) **"Neden?"** sütununu dolduran dosya.
`tools/build_movers.py` bu sütunu hiçbir zaman doldurmaz ("haber eşleştirmesi bekleniyor").
Ayrı bir zamanlanmış görev, kaynaklı haber başlıklarını bulup bu dosyayı
`data-feed:data/site/movers_news.json` yoluna yazabilir; sayfa dosya varsa birleştirir.

Kurallar:

- Yalnız **başlık + kaynak + yayın zamanı + bağlantı**. Haber metni, özet, görsel kopyalanmaz.
- Neden **tahmin edilmez**, yorum yazılmaz. Başlık yoksa `status: "ilgili haber bulunamadı"`.
- Kaynaklar kullanım şartları başlık + bağlantı göstermeye izin veren resmî akışlar (RSS/API) olmalı.
- `url` yalnız `https://` ile başlar; sayfa başka bağlantıyı göstermez.
- Eşleşme, `date` ve `symbol` alanlarının movers.json'daki `asof` ve `sembol` ile birebir aynı olmasıyla yapılır.

```json
{
  "schema": "phd.movers_news/1",
  "schema_version": 1,
  "source": "Piyasa Hava Durumu",
  "generated_at": "2026-11-23T07:10:00Z",
  "attribution": "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — türetilmiş veri",
  "entries": [
    {
      "date": "2026-11-20",
      "market": "abd",
      "symbol": "PDD",
      "items": [
        {"headline": "…", "source": "…", "url": "https://…", "published_at": "2026-11-20T12:05:00Z"}
      ]
    },
    {"date": "2026-11-20", "market": "bist", "symbol": "THYAO", "status": "ilgili haber bulunamadı"}
  ]
}
```

Alanlar:

| Alan | Tür | Açıklama |
|---|---|---|
| `entries[].date` | `YYYY-MM-DD` | movers.json'daki pazarın `asof` günü |
| `entries[].market` | `bist` \| `abd` \| `kripto` | pazar kimliği |
| `entries[].symbol` | metin | movers.json'daki `sembol` (BIST için `.IS` olmadan) |
| `entries[].items[]` | dizi | en çok 3 başlık; `published_at` UTC ISO 8601 |
| `entries[].status` | metin | `items` yoksa `"ilgili haber bulunamadı"` |

Sayfa yalnız 1–3 başlığı gösterir; birden fazlası varsa en yenisi önce.
