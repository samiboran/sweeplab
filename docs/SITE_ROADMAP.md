# Piyasa Hava Durumu — yol haritası

Çalışma dalı `site-dev` → tek PR "Piyasa sitesi (site-dev)" → `main` (birleştirmeyi
Boran yapar). Her zamanlanmış çalışma sıradaki ilk 1–2 işaretsiz maddeyi alır.

İlke: **herkese açık vitrin, özel motor.** Yalnızca çıktı (statik site + türetilmiş
veri) yayımlanır; puanlama kodu (`tools/`), ham girdiler (`data/derivs`,
`data/research`) ve yontem.html'in kelimelerle anlattığından fazla eşik
`piyasa/` veya `data/site/` içine girmez.

## Maddeler

- [x] S0 Kurallar v1 donduruldu: `docs/MAKRO_KURALLAR_v1.md` (tarih 2026-11-21, commit `4d8b1f6`). Sonraki eşik değişiklikleri = yeni sürüm; yayımlanmış skorlar yeniden yazılmaz. Dondurma öncesi günler "geriye dönük (retro)", sonrası "canlı (live)".
- [x] S1 Mimari + yayın planı: a) site `piyasa/` (vanilla, build yok), önizleme https://samiboran.github.io/sweeplab/piyasa/, günlük veri data-feed'den raw.githubusercontent.com ile (CORS doğrulandı); b) `docs/DEPLOY_PLAN.md` (A önerilen: Cloudflare Pages, B: GitHub Pro, C: ayrı public repo); c) workflow'da sırrı yoksa ATLANAN deploy işi. ⏸ Boran: hesap/token/repo.
- [x] S2 `tools/build_site.py` + testler: makro hava, yalnız türetilmiş veri → data-feed `data/site/` (today.json, history.csv, archive/YYYY-MM-DD.json); daily-brief.yml'de build_notebook.py sonrası hata-toleranslı adım; "Store data on data-feed" adımı `data/site/` ekler. Her kayıt: rules_version, mode, kaynak alanları. Lisanslı girdiler (HY OAS, S&P/Nasdaq) yalnız 0/1 + yön kelimesi. Cevap metinlerindeki tüm sayılar koddan (şablon cümle). Tazelik koruması (çekirdek girdi > 3 takvim günü eski ya da derleme hatası → "güncellenmedi" + son iyi tarih) ve hata halinde Boran'ın mevcut sohbetine kısa Telegram uyarısı. HISTORY kuralı.
- [x] S3 Sayfa `piyasa/index.html` (DESIGN): tarihli başlık, seviye (daire + kelime; "7/9" yalnız detayda), kural başına tek cümle (yontem.html bağlantılı), soru düğmeleri. Yasak kelimeler: al, sat, fırsat, ucuz, ucuzladı, hedef, kaçırma; 🚀 yok; tavsiye yok. Grafik kütüphanesi ve fontlar hariç < 100 KB. Footer: "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır." + veri tarihi + kural sürümü + © satırı.
- [ ] S4 TL katmanı + "Benim pozisyonum ne durumda?" hesaplayıcı: a) `tools/fetch_tl.py` (kendi hata-toleranslı adımı, data-feed `data/research/tl_1d/`; TRY=X, GC=F, SI=F, XU100.IS; ≥5 yıl backfill; gram altın/gümüş TL, BIST 100 USD; yalnız türetilmiş/yuvarlanmış değer ve % değişim; kaynak + şart riski kaydı); b) "TL tarafı" bölümü + küçük grafikler; c) `piyasa/hesapla.html` (tamamen istemci tarafı, ağ çağrısı yok, çerez yok, "bu cihazda hatırla" ile localStorage, "Girdiğin bilgiler cihazından çıkmaz."); d) birim testleri (102 TL/gr gümüş: USDTRY 50,58 → başabaş ons ≈ $62,7; USDTRY 60 → ≈ $52,9).
- [ ] S5 Grafikler: Lightweight Charts 4.1.3 (kök terminalle aynı, atıf korunur). BTC/ETH günlük kapanış + 50/200 gün ort.; makro seviye geçmişi (retro gri, live siyah/kırmızı, sürüm sınırları). Cevapların içinde.
- [ ] S6 Arşiv + sicil + SEO: `piyasa/arsiv.html`, "Sicil" görünümü (dondurma tarihinden itibaren, yanlış alarmlar dahil; kontrol yontem.html'de tanımlı), `piyasa/yontem.html`. SEO: başlık/açıklama, canonical, lang="tr", OG/Twitter, sitemap.xml + robots.txt (arama ve yapay zekâ tarayıcılarına izin), schema.org Dataset + WebSite JSON-LD, semantik HTML, alt metin, hızlı LCP, JS'siz tarayıcılar için bugünün ve arşivin statik HTML anlık görüntüsü. Lighthouse mobil ≥ 90 (SEO, a11y, perf) — skorlar kaydedilir.
- [ ] S7 Herkese açık Telegram kanalı: TELEGRAM_PUBLIC_CHANNEL_ID varsa (a) yayımlanan seviye değişince, (b) Pazar haftalık özet. Mesaj: seviye, değişen kurallar, bağlantı, "Yatırım tavsiyesi değildir." Yoksa ⏸ adımlarla.
- [ ] S8 Marka kancaları: `piyasa/config.js` (başlık, "İstatistik yalan söylemez", Altınkulak bağlantısı "Daha derin araçlar", X + Telegram yer tutucuları). Sunucusuz mümkünse günün başlık kartı og:image.
- [ ] S9 "Ortalamalara göre konum" tablosu (data/research/us_1d ve candles_1d'de 2026-11-13'ten yeni satır varsa; yoksa ⏸ "research-data PR bekleniyor"): sabit geniş evren (SPY, QQQ, SMH, GLD, SLV, BIST 100, BTC, ETH, mevcut büyükler), 20/50/200 gün ort. üstü/altı + 200 güne % uzaklık; alfabetik veya varlık sınıfına göre (en altta olana göre SIRALAMA YOK). BIST tekil hisse yok. Eylem kelimesi yok. yontem.html notu.
- [ ] S10 Makinece okunur Türkçe veri uçları: `data/site/` altında sabit, sürümlü JSON şeması (today.json, history.csv, tl.json, dunya.json, movers.json), `piyasa/veri.html` (Türkçe + kısa İngilizce): alanlar, güncelleme saati, lisans (yalnız kamu kaynaklı türetilmiş alanlar CC BY 4.0; lisanslı girdi alanları "yalnızca görüntüleme"), atıf biçimi. Uç yolları son barındırıcıda da aynı kalır.
- [ ] S10b "Dünya" bölümü — isteğe bağlı (`piyasa/dunya.html`, soru "Dünyada durum ne?", JSON yalnız açılınca): a) bölge tabloları (S9 biçimi; Japonya, Kore, Çin, Hong Kong, Tayvan, Brezilya; eksik endeksler için ETF'ler; her pazar için tarihli sabit 5–10 büyük şirket listesi, alfabetik); b) emtialar (GC, SI, PL, PA, HG, CL, BZ, NG + ücretsiz veri varsa buğday/soya/mısır; rodyum vb. "günlük serbest veri yok" referans tablosu — fiyat uydurulmaz); c) "Günün başlıkları": yalnız başlık + kaynak + saat + bağlantı, en çok ~10, şartları izin veren resmi RSS'lerden; d) `data/site/dunya.json`, kendi adımı.
- [ ] S10c "Günün hareketlileri ve anomaliler" — isteğe bağlı (`piyasa/hareket.html`, soru "Bugün piyasada neler oldu?"): a) evren config'i (BIST 100, research-data ABD listesi, en büyük ~30 kripto; likidite tabanı); b) pazar başına en çok yükselen/düşen 5 (% değişim, göreli hacim, endeks hareketi); c) kural tabanlı anomaliler (hacim ≥ 3× 20g ort., açılış boşluğu ≥ ±%5 hisse / ±%8 kripto, hareket ≥ 3× ATR(14), 52 hafta zirve/dip, endeksine ters > 3 puan) + düz Türkçe gerekçe; d) "Neden?" sütunu: "haber eşleştirmesi bekleniyor"; `movers_news.json` şeması docs/'ta; neden uydurulmaz; e) haber dili, uyarı, veri tarihi; `data/site/movers.json` kendi adımı (zamanlama belgelenir).
- [ ] S11 İzleyicisiz ölçüm: config.js'ten beslenen google-site-verification (ve Bing) meta yer tutucusu; DEPLOY_PLAN.md'de Search Console ve (A seçilirse) Cloudflare çerezsiz Web Analytics rehberi. Üçüncü taraf analitik yok.
- [ ] S12 PARK — gelir modeli (yalnız gerçek kitle olunca; kod/cüzdan/hesap yok): `docs/MONETIZATION_PLAN.md` — (1) Türkiye pazarı türetilmiş verinin ücretli API katmanı, (2) x402 / Cloudflare Monetization Gateway (insanlar ve arama motorları ücretsiz), (3) önkoşullar: özel motor, Yahoo/FRED-kısıtlı girdilerin lisanslı kaynaklarla değişimi, alan adı, Cloudflare, Türkiye'de hukuki/vergi kontrolü (SPK, MASAK, kripto varlık kanunu) — sermaye piyasası avukatıyla. Riskler ve yeniden bakma tetikleyicileri.

## Kararlar

- **Barındırma (önizleme):** GitHub Pages şu an `main` dalının kökünden yayın
  yapıyor (repo'da Pages workflow'u yok; README'deki demo adresi kökü gösteriyor).
  `piyasa/` klasörü main'e birleşince otomatik olarak
  `https://samiboran.github.io/sweeplab/piyasa/` adresinde yayına girer; Pages
  kaynağı **değiştirilmedi**, kök SweepLab terminali etkilenmez.
- **Günlük veri, main'e günlük commit olmadan:** sayfa JSON'u
  `https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/…`
  adresinden çeker. 2026-11-21'de doğrulandı: `access-control-allow-origin: *`,
  `cache-control: max-age=300` (en çok 5 dk gecikme). Son barındırıcıda (A/C)
  deploy işi `data/site/` klasörünü sitenin yanına kopyalar ve sayfa göreli
  `data/site/` yolunu kullanır (repo özel olunca raw adresi çalışmaz). Seçim
  `piyasa/` içindeki tek bir veri-kaynağı ayarıyla yapılacak (S3).
- **Fontlar:** Inter 5.1.0 (@fontsource, SIL OFL) `piyasa/fonts/` altında kendi
  sunucumuzdan — latin + latin-ext (ğ ş ı İ). Font CDN'i yok → CSP `font-src
  'self'`, SRI gerekmez, üçüncü tarafa istek yok.
- **Grafik kütüphanesi:** kök terminalin sabitlediği Lightweight Charts 4.1.3
  (cdnjs), SRI ile (S5).
- **Veri yolu (S3):** `app.js` `*.github.io` üzerinde raw data-feed adresini, diğer
  tüm hostlarda (Cloudflare / ayrı repo / yerel önizleme) göreli `data/site/`
  yolunu kullanır — deploy işleri `data/site/` klasörünü sitenin yanına koyar.
- **Lisanslı girdiler (S2):** HY OAS, Nasdaq 100 **ve ICE dolar endeksi (DXY)**
  yalnız 0/1 + yön kelimesi olarak yayımlanır (DXY ICE lisanslı olduğu için
  temkinli olarak listeye eklendi). VIX (Cboe) 1 ondalıkla yayımlanıyor — K2
  kuralı seviyeye dayalı; para kazanma öncesi lisans kontrolü gerekir (S12).
- **Tazelik (S2):** günlük girdiler en çok 3 iş günü (hafta sonu sayılmaz),
  haftalık Fed net likiditesi en çok 10 takvim günü eski olabilir. Aşılırsa
  history'e satır eklenmez, today.json `status: "güncellenmedi"` + son iyi
  tarih, Telegram uyarısı (yalnız zamanlanmış/elle çalıştırmada).
- **Seviye dairesi (S3):** KIRMIZI = dolu kırmızı daire, SARI = kırmızı halka,
  YEŞİL = siyah halka — tek vurgu rengi kuralı korunur.
- **Kural girdisi:** `notebook_daily.json` 60 günlük pencere tutuyor; bu yüzden
  `history.csv` ve `archive/` yalnız ekleme yapılan ayrı dosyalar (HISTORY kuralı).

## Güvenlik kontrol listesi

- [x] `piyasa/` ve `data/site/` içinde sır/token/API anahtarı yok (her push öncesi tarama)
- [x] Workflow'da en az yetki: deploy işleri `contents: read`; sırrı yoksa iş atlanır
- [x] Loglara sır yazdırılmıyor (deploy adımları token'ı yalnız env üzerinden kullanır)
- [x] CSP `<meta http-equiv>` (self + tam CDN hostu; unsafe-eval yok, satır içi stil/script yok), referrer-policy — index.html + yontem.html (S3)
- [ ] CDN varlıklarında SRI + sabit sürüm (S5)
- [x] Çekilen JSON / haber / kullanıcı girdisi yalnız textContent/DOM API ile (app.js'te innerHTML yok); dış bağlantılar `rel="noopener noreferrer"` (S3; sonraki sayfalarda da korunacak)
- [x] Üçüncü taraf izleyici/analitik yok, çerez yok

## Notlar

- **2026-11-21** — S0 + S1 tamam. `site-dev` main'den (`1273399`) açıldı.
  Kurallar v1 donduruldu; 2026-11-19 satırı elle doğrulandı: ham skor 7 →
  KIRMIZI (kalıcı test S2'de). raw.githubusercontent CORS doğrulandı.
  `docs/DEPLOY_PLAN.md` yazıldı; daily-brief.yml'e sırrı yoksa atlanan iki
  deploy işi (C: `SITE_DEPLOY_TOKEN`+`SITE_DEPLOY_REPO`, A:
  `CLOUDFLARE_API_TOKEN`+`CLOUDFLARE_ACCOUNT_ID`) eklendi. `piyasa/` içinde
  tasarım dilini taşıyan yer tutucu sayfa + fontlar. Kalan: Mart 2020 / 2022 /
  Ağustos 2024 sağlama notu (isteğe bağlı, belge). ⏸ Boran: hesap/token/repo
  (DEPLOY_PLAN.md). Mevcut 23 test geçti.
- **2026-11-21 (2. çalışma)** — S2 + S3 tamam. `tools/build_site.py`: v1
  kuralları, gürültü filtresi, yalnız-ekleme `history.csv` + `archive/`
  (ilk çalışmada 60 notebook satırı retro olarak doldurulur; bugün yerelde
  denendi: 2026-11-20 → ham 7, KIRMIZI), tazelik koruması, hata/eski veri
  Telegram uyarısı, şablon cevaplar (5 soru). daily-brief.yml'e
  build_notebook sonrası hata-toleranslı adım + data-feed'e `data/site/`
  ekleme. `tests/test_build_site.py` (12 test; 2026-11-19 → 7 → KIRMIZI dahil),
  toplam 35 test geçti. `piyasa/index.html` + `app.js` + kısa `yontem.html`
  (S6'da genişleyecek); HTML+CSS+JS ≈ 20 KB. Not: `data/site/` data-feed'de
  ancak PR main'e birleşip workflow çalışınca oluşur; o zamana kadar Pages
  önizlemesi "Veri şu an yüklenemedi" gösterir (ekran görüntüleri yerel
  derlemeyle alındı). İlk canlı kayıt 22 Kasım sabahı (veri tarihi 21 Kasım)
  bekleniyor — birleştirme öncesi çalışmalar retro kalır.
