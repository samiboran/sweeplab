# Makro hava kuralları v2 — TASLAK (yürürlükte değil)

Durum: öneri. v1 (`docs/MAKRO_KURALLAR_v1.md`) yürürlükte kalır; yayımlanmış skorlar yeniden yazılmaz.
Neden: dış değerlendirmede (22 Kasım 2026, iki bağımsız model) "makro hava tamamen ABD verisi; TL yatırımcısına
ne anlattığı belirsiz" eleştirisi. Boran 22 Kasım'da yönü onayladı; zamanlama acil değil.

## Önerilen ek başlık: Türkiye (0–2 puan)

| Kod | Kural (taslak) | Kaynak | Not |
|---|---|---|---|
| T1 | Dolar/TL 20 günde olağan seyrinin belirgin üstünde arttı | TCMB EVDS (resmî gösterge kuru) | TL'nin "planlı" değer kaybı her ay var; eşik bunun üstünü yakalamalı (ör. 20 günlük artış, önceki 12 ayın 20 günlük artışlarının en yüksek %10'una girdiyse). |
| T2 | BIST 100 dolar bazında 20 günde ≥ %8 düştü | BIST 100 + dolar/TL (bugün Yahoo; lisanslı kaynak gerekli) | Yalnız 0/1 ve yön kelimesi yayımlanır. |

Değerlendirilip **eklenmeyenler**: Türkiye 5 yıllık CDS (serbest günlük kaynak yok), TCMB faiz kararı (olay, günlük
seri değil; "Bu hafta" takviminde zaten var).

Toplam 0–11 olur; seviye sınırları da yeniden yazılmalı (ör. 0–2 YEŞİL, 3–5 SARI, 6+ KIRMIZI). Kesin eşikler
Boran'ın kararıdır; geçmiş veriye göre "en iyi sonucu veren" eşik aranmaz (v1 ilkesi).

## Geçiş adımları

1. ⏸ Boran: TCMB EVDS'ye üye ol (evds2.tcmb.gov.tr → Giriş → Üye ol), profil sayfasından API anahtarını al,
   repo'ya `EVDS_API_KEY` sırrı olarak ekle (Settings → Secrets and variables → Actions → New repository secret).
2. Eşikler yazılı olarak dondurulur → `docs/MAKRO_KURALLAR_v2.md` (tarih + commit).
3. En az 4 hafta **gölge çalışma**: v2 skoru hesaplanır, yalnız data-feed'in özel tarafına yazılır, yayımlanmaz.
4. Yayın günü: `rules_version: "v2"`. Önceki günler v1 olarak kalır; grafikte sürüm sınırı işaretli (S5'te var).
   Sicil v1 ve v2 için ayrı tutulur.
5. yontem.html'de Türkiye başlığı ve eşiklerin gerekçesi sade Türkçeyle (TR + EN).
