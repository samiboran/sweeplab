# Devir notu: ABD hisseleri momentum demo (14.10.2026)

Yeni oturum bunu okuyup buradan devam etsin. Kripto "Kaldıraç Gözlem Defteri" ayrı oturumda yürüyor; bu iş ona karışmasın.

## Amaç
Martin Luk / Qullamaggie tarzı momentum-geri çekilme stratejisini ABD hisselerinde
TradingView deneme hesabında (5.000 $) 3–4 hafta uygulamak, her işlemi kaydedip R ve kazanma oranını ölçmek.

## Kurallar (önceden sabitlendi)
- Filtre: 1 ay veya 3 ay getiri >= %30, EMA9 > EMA21 > EMA50 (EMA21 yükseliyor), ADR20 >= %5
- Ortam: SPY 200 günlük ortalamanın üstündeyse işlem (altındayken test negatifti)
- Giriş: fiyat EMA9/21'e çekilip EMA9'u geri alınca (günlük kapanış ya da 5–15 dk dönüş)
- Stop: kurulum günü dibinin / EMA21'in altı (%1–8)
- Çıkış: +3R'da %20 sat, kalan günlük kapanış EMA9 altına inince (alternatif EMA21)
- Risk: işlem başı hesabın %1'i (5.000 $ → 50 $), aynı anda en fazla 3–4 pozisyon, hisseler 1x
- Short'lar test edilmedi; sadece küçük boyutla gözlem

## Test sonucu (95 hisse, günlük, 2021–2026; tools/ ve scratchpad'deki bt_us.py)
- 2021–23: +0,03R/işlem (n=217) · 2024–26: +0,50R (n=557, EMA21 takip +0,76R), kazanma ~%29
- SPY>MA200 iken +0,45R, altında −0,29R · Kârın çoğu birkaç büyük kazanandan (VKTX, AFRM, MSTR, SMR, IONQ)
- Rastgele giriş (aynı filtre) benzer/daha iyi → avantaj filtre + çıkış sisteminden, geri çekilme zamanlamasından değil
- Uyarı: evren bugünün popüler hisselerinden seçildi (hayatta kalma yanlılığı). 2026 YTD ~0.
- Aynı kurallar kriptoda (30 coin) 2024–26 negatif çıktı (−0,29R) → kriptoda uygulanmıyor.

## 14.10.2026 aday listesi (13.10 kapanışına göre)
Long (tetik / stop / 3R): MRNA 216 (kurulum) / 203,5 / ~253 · AMD 614 üstü / 594 / ~675 ·
MRVL 271 üstü / 259 / ~306 · CRWD 266 üstü / 255 / ~297 · MSTR 155 üstü / 147 / ~179
Geri çekilme bekle: SHOP ~166 (stop 160) · PLTR ~200 (stop 189) · ZS ~218 (stop 206)
Short gözlem: APP ~280 başarısız tepki (stop 295) · ASTS 52–54 (stop 58)
Bunlar tools/stock_plan.json'da; sabah raporu seviye alarmı veriyor.

## Kullanıcının gerçek portföyü (Midas, ~800 $)
SPCX (plan: 150 ve 135'te ekle, 180 üstü kapanışta ekle; 9 Aralık civarı lock-up bitişi),
PLUG ~100 $, EOSE ~100 $ (ikisi de düşüş trendinde; "yanıldım" seviyesi: PLUG 1,55, EOSE 2,29 altı kapanış).

## Altyapı
- Veri: .github/workflows/research-data.yml (dispatch) → data-feed:data/research/us_1d/*.csv (Yahoo 5y)
- Tarama/test kodu: tools/fetch_us_universe.py; test betiği şu an scratchpad'de (bt_us.py) — repo'ya alınabilir
- Hisse alarmları: tools/stock_plan.json + tools/daily_brief.py (stock_plans)

## Yapılacaklar
- [ ] Deneme hesabı ayarları: teminat kontrolü açık, hisse 1x, kripto 5x, komisyon %0,05
- [x] "Demo işlemler" kaydı (ayrı sayfa): https://claude.ai/artifact/HGLb369A3BEcxYoriT7uDh
  - Veri artifact'ın kendi deposunda: `trades` koleksiyonu (her işlem bir belge), `plan/current` (aday listesi: asOf, items[sym, kind long|wait|short, trigger, stop, target, note])
  - R komisyon dahil hesaplanır (%0,05 giriş + çıkış); kısmi satış (varsayılan %20) ağırlıklı ortalamaya girer
  - Claude bu depoyu okuyup yazabilir: değerlendirmede `trades` okunur, günlük taramada `plan/current` güncellenir
- [ ] Günlük tarama işini otomatikleştir (her sabah 10 aday + tetik seviyeleri)
- [ ] 3–4 hafta sonra değerlendirme: R ortalaması > 0 mı, kurallara uyuldu mu
