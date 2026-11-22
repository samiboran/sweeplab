# ozet.json — "Günün özeti" (phd.ozet/1)

Her sabah ayrı bir zamanlanmış Claude görevi hazırlar; sitede canlı yapay zekâ yoktur.
Görev, dosyayı `data-feed` dalına `data/site/ozet.json` olarak yazar, aynı içeriği
`data/site/ozet/YYYY-MM-DD.json` arşivine ekler (yalnız ekleme) ve push öncesi
`python3 tools/check_ozet.py data/site/ozet.json` ile doğrular. Ana sayfa "Günün özeti"
bölümünde gösterir (TR ve EN).

## Yazım kuralları

- **Kaynak:** yalnız kullanım şartları başlık + bağlantı göstermeye izin veren kaynaklar: merkez
  bankaları ve resmî kurumlar (TCMB, Fed, ECB, BoJ, TÜİK, BLS, EIA…), şirket basın odaları, sektör
  kuruluşları (World Gold Council, Silver Institute, LBMA), resmî RSS'i olan haber kaynakları.
  Ücretli/üyelikli içerik, TradingView ve şartları otomatik erişimi yasaklayan siteler kullanılmaz.
- **Kendi cümlelerimizle:** metin kopyalanmaz, alıntı yapılmaz; 2–3 cümlelik olgusal özet. Haberdeki
  iddia kaynağa atfedilir ("Fed'in açıklamasına göre…"). Sayılar kaynakta yazdığı gibi.
- **Yorum ve tavsiye yok:** "al/sat", "fırsat", "ucuz", hedef fiyat, tahmin, yön beklentisi yok;
  nedeni kaynak söylemiyorsa neden yazılmaz.
- En çok 8 öğe; her öğede 1–3 kaynak bağlantısı (`https://`), konu listesi sabittir.
- Görüntü, video, haber gövdesi alınmaz.

## Alanlar

```json
{
  "schema": "phd.ozet/1", "schema_version": 1,
  "source": "Piyasa Hava Durumu", "site_url": "https://samiboran.github.io/sweeplab/piyasa/",
  "generated_at": "2026-11-23T06:45:00Z", "date": "2026-11-23",
  "attribution": "Kaynak: Piyasa Hava Durumu (samiboran.github.io/sweeplab/piyasa) — özetler kendi cümlelerimizle; haberlerin hakları kaynaklarına aittir",
  "method": "Resmî kaynaklar ve izinli akışlar tarandı; olgusal özet, yorum ve tavsiye yok.",
  "items": [
    {
      "konu": "Merkez bankaları",
      "baslik": "…", "ozet": "…",
      "baslik_en": "…", "ozet_en": "…",
      "kaynaklar": [{"ad": "Federal Reserve", "url": "https://…", "zaman": "2026-11-22T19:00:00Z"}]
    }
  ]
}
```

`konu`: Türkiye · Merkez bankaları · Dünya ekonomisi · Altın ve emtia · Kripto · Şirketler · Asya · Latin Amerika.
Sayfa `date` 2 günden eskiyse bölümü göstermez.
