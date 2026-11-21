# Makro hava kuralları — v1 (DONDURULDU)

**İç kural kitabı.** Herkese açık sayfa (`piyasa/yontem.html`) bu kuralları düz
Türkçe ile anlatır; eşiklerin tam listesi yalnızca bu dosyada ve motor kodunda
(`tools/build_site.py`) bulunur. Bu dosya `piyasa/` veya `data/site/` içine
kopyalanmaz.

| Alan | Değer |
|---|---|
| Sürüm | `v1` (`rules_version: "v1"`) |
| Dondurulma tarihi | **2026-11-21** |
| Dondurulduğu commit | `4d8b1f6` (site-dev) |
| Taban (main) commit | `1273399` |
| Girdi | `data/derivs/notebook_daily.json` → `rows[]` (data-feed dalı) |

## Sürüm kuralı

- Eşik veya kural değişikliği = **yeni sürüm** (v1.1, v1.2, v2 …), yeni bir
  `docs/MAKRO_KURALLAR_vX.md` dosyası ve yeni dondurulma tarihi.
- **Yayımlanmış skorlar asla yeniden yazılmaz.** Her kayıt kendi
  `rules_version` değerini taşır. Grafiklerde sürüm sınırları işaretlenir.
- Bir hata düzeltmesi (bug) gerekiyorsa: düzeltme belgelenir, eski kayıt
  `archive/` içinde korunur, düzeltme notu eklenir.

## Mod: geriye dönük (retro) / canlı (live)

- `mode: "live"` — skor, veri tarihi **2026-11-21 veya sonrası** olan bir gün
  için, o günkü günlük derlemede (daily-brief workflow) hesaplanıp yayımlandı.
- `mode: "retro"` — dondurulma tarihinden önceki her gün **ve** sonradan
  doldurulan (backfill) her kayıt. Retro kayıtlar sicile (track record)
  sayılmaz; yalnızca bağlam olarak gösterilir.

## Tanımlar

- Satırlar tarihe göre sıralı `notebook_daily.json → rows`.
- **"20g"** = son satır ile **20 satır önceki** satır karşılaştırması (20 satır
  yoksa en eski satır).
- "değişim %" = `(son / önceki − 1) × 100`; "değişim/yükseliş" (yüzde değil) =
  `son − önceki`, girdinin kendi biriminde.
- Eksik değer (`null`) olan kural **0 puan** alır ve kayıtta `null` olarak
  işaretlenir (bayrak "veri yok").

## Kurallar (her biri 1 puan)

### Likidite (0–3)
| Kod | Kural |
|---|---|
| `L1` | `regime.stables_7d_pct < 0` (stablecoin arzı 7 günde azaldı) |
| `L2` | 20g değişimi `regime.netliq_musd < 0` (Fed net likiditesi düştü) |
| `L3` | 20g yükselişi `regime.real10y ≥ 0.15` (10 yıllık reel faiz ≥ 15 bp arttı) |

### Dolar (0–1)
| Kod | Kural |
|---|---|
| `D1` | 20g değişimi `regime.dxy ≥ +%1` |

### Kredi / risk (0–3)
| Kod | Kural |
|---|---|
| `K1` | 20g yükselişi `risk.hy_oas ≥ 0.25` (yüksek getirili tahvil spread'i ≥ 25 bp açıldı) — **lisanslı girdi: yalnızca 0/1 bayrak + yön kelimesi yayımlanır** |
| `K2` | `risk.vix ≥ 18` |
| `K3` | 20g değişimi `risk.ndx ≤ −%3` — **lisanslı endeks: yalnızca 0/1 + yön kelimesi** |

### Nakde kaçış (0–1)
| Kod | Kural |
|---|---|
| `N1` | 20g değişimi `macro.gold ≤ −%3` **VE** 20g `dxy` değişimi `> 0` |

### Petrol (0–1)
| Kod | Kural |
|---|---|
| `P1` | 20g değişimi `macro.wti ≥ +%10` → etiket "enflasyon dürtüsü"; **VEYA** (`≤ −%15` **VE** 20g `hy_oas` değişimi `> 0`) → etiket "talep zayıflığı" |

## Skor ve seviye

- Ham skor = puanların toplamı, **0–9**.
- Seviye: **0–2 YEŞİL**, **3–4 SARI**, **5+ KIRMIZI**.
- **Gürültü filtresi:** Yayımlanan seviye ancak bugünün **ve** dünün ham skoru
  aynı yeni seviyeye düşüyorsa değişir. Aksi halde önceki yayımlanan seviye
  korunur ve kayıtta bu açıkça yazılır (`level_held: true`, "Ham skor X
  seviyesine işaret ediyor; değişim için ikinci gün onayı bekleniyor").
- İlk gün (önceki yayımlanmış seviye yoksa) seviye = ham skorun seviyesi.

## Doğrulama örneği (birim testi)

`2026-11-19` satırı (20g karşılaştırması `2026-10-30` ile):

| Kod | Girdi | Bayrak |
|---|---|---|
| L1 | stables_7d_pct = −1,33 | 1 |
| L2 | netliq 20g değişimi ≥ 0 | 0 |
| L3 | real10y +0,28 | 1 |
| D1 | dxy +%1,98 | 1 |
| K1 | hy_oas +0,08 | 0 |
| K2 | vix 24,56 | 1 |
| K3 | ndx −%6,1 | 1 |
| N1 | altın −%5,5 ve dxy > 0 | 1 |
| P1 | wti −%20,1 ve hy_oas değişimi > 0 → "talep zayıflığı" | 1 |

**Ham skor 7 → KIRMIZI.** (Hesap 2026-11-21'de data-feed verisiyle elle
doğrulandı; S2'de `tests/test_build_site.py` bunu kalıcı test olarak içerecek.)

## Sağlama notu (ayar yok)

Mart 2020, 2022 ortası ve Ağustos 2024 için v1'in ne göstereceği, kolay
erişilebilir kamu verisiyle ileride yalnızca **belge** olarak eklenebilir.
Eşikler bu nota göre değiştirilmez.

## Kayıt

- 2026-11-21 — v1 donduruldu, commit `4d8b1f6`.

## Netleştirme — veri günü (2026-11-21, ilk canlı kayıttan önce)

Eşikler ve kurallar değişmedi; yalnız **hangi günün** puanlanacağı netleştirildi:

- Bir gün ancak **tamamlanmışsa** puanlanır: her günlük çekirdek girdi o günün
  (hafta sonu satırı için önceki cuma) değerini taşımalı; ya da kaynak o gün veri
  yayımlamadıysa (ABD tatili) sonraki bir satır daha yeni değeri taşımalı.
- Neden: sabah derlemesinin en yeni satırı (dün) çoğunlukla bir önceki günün ABD
  verisini taşır (FRED; VIX, reel faiz, HY OAS bir gün geç yayımlanır). Bu satırı
  puanlamak iki farklı günü karıştırıyordu.
- Sonuç: yayımlanan veri günü genellikle takvim gününden 2 gün geridedir; sayfada
  "Veri: … kapanışı" olarak açıkça yazılır.
- Geriye dönük kayıtlar için "20g" karşılaştırması, saklanan eski notebook
  sürümlerinden **tam 20 satırla** yapılır ("en eski satır" yedeği yalnız veri
  yoksa).
- Aynı gün belgelenmiş düzeltme: 2026-09-22..2026-10-05 arası 11 geriye dönük
  kayıt yeniden hesaplandı (arşivde `duzeltme` alanı, önceki değerleriyle);
  tamamlanmamış 2026-11-20 kaydı kaldırıldı (tamamlanınca eklenecek).
