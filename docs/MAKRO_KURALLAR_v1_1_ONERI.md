# v1.1 önerisi — Petrol kuralı (P1) — KARAR BORAN'DA

Durum: **öneri, uygulanmadı.** v1 donduruldu; bu değişiklik yalnız Boran onaylarsa
yeni sürüm (v1.1) olarak, onay tarihinden itibaren geçerli olur. Yayımlanmış v1
skorları değişmez.

## Sorun (Boran'ın tespiti, 2026-11-21)

v1'de P1'in düşüş kolu: WTI 20 günde ≤ −%15 **ve** HY risk primi 20 günde > 0
(herhangi bir artış) → "talep zayıflığı".

- Ekim 2026'da petrol kısa bir sıçrama yaptı (WTI ~91 → ~104 $, Brent ~117 $) ve
  Kasım başında geri döndü (~83–86 $).
- Aynı sıçrama iki kez puan aldı: yükselişte "enflasyon dürtüsü" (19–20 Ekim…),
  geri dönüşte "talep zayıflığı" (Kasım). 20 günlük karşılaştırma günü zirveye
  denk gelince düşüş olduğundan büyük görünüyor.
- "> 0" kredi koşulu çok gevşek: 19 Kasım'da HY primi 20 günde yalnız +0,08 puan
  açılmıştı (K1 eşiği 0,25), yine de "talep zayıflığı" dendi.

## Öneri (v1.1)

Düşüş kolu ancak şu ikisi birlikteyse işaret verir:
1. WTI 20 günde ≤ −%15, **ve**
2. HY risk primi 20 günde **≥ 0,25 puan** açıldı (K1 ile aynı eşik: kredi
   tarafında gerçek gerginlik teyidi).

Yükseliş kolu (≥ +%10, "enflasyon dürtüsü") aynı kalır.

## Etkisi (Ekim–Kasım 2026, history.csv üzerinde)

| Gün | v1 ham skor | v1.1 ham skor | Seviye |
|---|---|---|---|
| 2026-11-18 | 7 | 6 | KIRMIZI → KIRMIZI |
| 2026-11-19 | 7 | 6 | KIRMIZI → KIRMIZI |

Diğer "talep zayıflığı" günlerinde HY primi zaten ≥ 0,25 açılmıştı; değişmez.
Seviye hiçbir günde değişmiyor.

## Bu arada yapılan (kural değişikliği değil)

- Cümle artık "talep zayıflığı" demiyor, "kural bunu **olası** talep zayıflığı
  işareti sayar" diyor; karşılaştırma günü 60 günlük zirveye yakınsa "düşüşün bir
  kısmı önceki ani yükselişin geri alınmasıdır; arz ve jeopolitik etkenler de rol
  oynayabilir" bağlamı ekleniyor (yalnız bilgi; puanı değiştirmez).
