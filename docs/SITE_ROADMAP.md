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
- [x] S4 TL katmanı + "Benim pozisyonum ne durumda?" hesaplayıcı: a) `tools/fetch_tl.py` (kendi hata-toleranslı adımı, data-feed `data/research/tl_1d/`; TRY=X, GC=F, SI=F, XU100.IS; ≥5 yıl backfill; gram altın/gümüş TL, BIST 100 USD; yalnız türetilmiş/yuvarlanmış değer ve % değişim; kaynak + şart riski kaydı); b) "TL tarafı" bölümü + küçük grafikler; c) `piyasa/hesapla.html` (tamamen istemci tarafı, ağ çağrısı yok, çerez yok, "bu cihazda hatırla" ile localStorage, "Girdiğin bilgiler cihazından çıkmaz."); d) birim testleri (102 TL/gr gümüş: USDTRY 50,58 → başabaş ons ≈ $62,7; USDTRY 60 → ≈ $52,9).
- [x] S4-fix Yahoo `range=max` günlük değil AYLIK bar döndürüyor (21 Kasım ilk çalışmada tl.json değişimleri aylık barlardan hesaplandı). Uzun geçmiş artık period1/period2 ile günlük çekiliyor; günlük olmayan depo otomatik yeniden kuruluyor; günlük olmayan bardan türetme yapılmıyor (`is_daily`).
- [x] S5 Grafikler: Lightweight Charts 4.1.3 (kök terminalle aynı, atıf korunur). BTC/ETH günlük kapanış + 50/200 gün ort.; makro seviye geçmişi (retro gri, live siyah/kırmızı, sürüm sınırları). Cevapların içinde.
- [x] S6 Arşiv + sicil + SEO: `piyasa/arsiv.html`, "Sicil" görünümü (dondurma tarihinden itibaren, yanlış alarmlar dahil; kontrol yontem.html'de tanımlı), `piyasa/yontem.html`. SEO: başlık/açıklama, canonical, lang="tr", OG/Twitter, sitemap.xml + robots.txt (arama ve yapay zekâ tarayıcılarına izin), schema.org Dataset + WebSite JSON-LD, semantik HTML, alt metin, hızlı LCP, JS'siz tarayıcılar için bugünün ve arşivin statik HTML anlık görüntüsü. Lighthouse mobil ≥ 90 (SEO, a11y, perf) — skorlar kaydedilir. **+ Boran isteği (21 Kasım):** ana sayfada "Tarih seç" — geçmiş bir günün makro havasını `archive/YYYY-MM-DD.json` dosyasından aynı düzende gösterir (o günün kaydı neyse o; yeniden hesaplanmaz).
- [x] S6b **Boran isteği (21 Kasım): "Dünyada bu Pazartesi" / "Dünyada bu Cuma"** (`piyasa/hafta.html`, `tools/build_week.py`, `data/site/hafta.json` + `hafta/YYYY-MM-DD.json`): her pazartesi ve cuma (İstanbul) — gram altın, gram gümüş, dolar/TL, BIST 100 (dolar bazında), SPY, QQQ, BTC'nin son 10 yılda aynı takvim haftasındaki seyri (kaç yıl yükseldi/düştü, ortanca, en güçlü/zayıf yıl, yıl yıl çubuk); cuma baskısında bu haftanın şimdiye kadarki hareketi ve geçmiş yıllar içindeki yeri; haftanın ABD veri takvimi (FOMC/TÜFE/istihdam); "Tarihte bu hafta" + "İlkler" (`tools/tarihte.json`: yalnız kaynak bağlantılı girdiler; kaynaksız girdi yayımlanmaz). Tahmin yok, tavsiye yok. **Her zamanlanmış çalışma:** önümüzdeki iki haftanın tarihlerine düşen, kaynağı doğrulanmış 3–6 ekonomi tarihi girdisi + 1 "ilk" ekler (dünya ve Türkiye; vergi, sanayi ilkleri, piyasa krizleri, merkez bankaları, emtia). Sonra: TCMB PPK takvimi (resmî kaynaktan), SPY/QQQ için 2000'den beri geçmiş (fetch_tl'e eklendi; ilk çalışmada dolar), ara sıra "Karşılaştırma" (ör. OECD vergi rekabeti sıralaması, Türkiye satırı vurgulu, kaynak + lisans kontrolü).
- [x] S7 Herkese açık Telegram kanalı: `tools/post_public.py` (daily-brief.yml'de hata-toleranslı adım; TELEGRAM_PUBLIC_CHANNEL_ID yoksa atlanır). Aynı bot; (a) yayımlanan seviye değişince (yalnız canlı satır; geriye dönük doldurma asla gönderilmez), (b) Pazar (İstanbul) haftalık özet. Mesaj: seviye, değişen kurallar, bağlantı, "Yatırım tavsiyesi değildir." Çift gönderim `data/derivs/public_channel_state.json` ile engellenir. ⏸ **Boran:** (1) Telegram'da Yeni Kanal → Herkese açık → kullanıcı adı (ör. `@piyasahavadurumu`); (2) Kanal → Yöneticiler → Yönetici ekle → SweepLab botu (yalnız "Mesaj gönder" yetkisi yeterli); (3) GitHub → sweeplab → Settings → Secrets and variables → Actions → New repository secret: `TELEGRAM_PUBLIC_CHANNEL_ID` = `@kanaladi` (ya da `-100…` sayısal kimlik); (4) isteğe bağlı: `piyasa/config.js` içinde `telegram: "https://t.me/kanaladi"`.
- [x] S8 Marka kancaları: `piyasa/config.js` (başlık, "İstatistik yalan söylemez" — her sayfanın başlığında, Altınkulak bağlantısı "Daha derin araçlar" altbilgide, X + Telegram yer tutucuları boşsa gizli, S11 doğrulama kodu alanları). og:image: `tools/build_og.py` her sabah `data/site/og.png` (1200×630, Inter, tek kırmızı vurgu; Pillow yoksa sabit `piyasa/og.png` marka kartı kopyalanır), ana sayfa `summary_large_image`; diğer sayfalar sabit kart.
- [x] S9 "Ortalamalara göre konum" tablosu (data/research/us_1d ve candles_1d'de 2026-11-13'ten yeni satır varsa; yoksa ⏸ "research-data PR bekleniyor"): sabit geniş evren (SPY, QQQ, SMH, GLD, SLV, BIST 100, BTC, ETH, mevcut büyükler), 20/50/200 gün ort. üstü/altı + 200 güne % uzaklık; alfabetik veya varlık sınıfına göre (en altta olana göre SIRALAMA YOK). BIST tekil hisse yok. Eylem kelimesi yok. yontem.html notu.
- [x] S10 Makinece okunur Türkçe veri uçları: `data/site/` altında sabit, sürümlü JSON şeması (today.json, history.csv, tl.json, dunya.json, movers.json), `piyasa/veri.html` (Türkçe + kısa İngilizce): alanlar, güncelleme saati, lisans (yalnız kamu kaynaklı türetilmiş alanlar CC BY 4.0; lisanslı girdi alanları "yalnızca görüntüleme"), atıf biçimi. Uç yolları son barındırıcıda da aynı kalır.
- [x] S10b "Dünya" bölümü — isteğe bağlı (`piyasa/dunya.html`, soru "Dünyada durum ne?", JSON yalnız açılınca): a) bölge tabloları (S9 biçimi; Japonya, Kore, Çin, Hong Kong, Tayvan, Brezilya; eksik endeksler için ETF'ler; her pazar için tarihli sabit 5–10 büyük şirket listesi, alfabetik); b) emtialar (GC, SI, PL, PA, HG, CL, BZ, NG + ücretsiz veri varsa buğday/soya/mısır; rodyum vb. "günlük serbest veri yok" referans tablosu — fiyat uydurulmaz); c) "Günün başlıkları": yalnız başlık + kaynak + saat + bağlantı, en çok ~10, şartları izin veren resmi RSS'lerden; d) `data/site/dunya.json`, kendi adımı. **+ Boran isteği (21 Kasım):** geniş ekranda (≥ 1200 px) ana sayfanın sağ boşluğuna kısa bir "Dünya" sütunu (Japonya, Kore, Çin… 1g değişim + "Günün başlıkları" ilk 5 başlık); yalnız geniş ekranda ve dunya.json gelince yüklenir; telefonda soru düğmesi olarak kalır. **+ Boran (21 Kasım):** "Günün başlıkları"na büyük şirket haberleri, teknoloji, emtia ve değerli madenler başlıkları; Midas ("Midas'ın Kulakları", getmidas.com) ana başlıkları yalnız kullanım şartları/robots izin veriyorsa ve resmi bir akış (RSS/API) varsa — yalnız başlık + kaynak + saat + bağlantı; izin yoksa ⏸ ve Boran'a sorulacak.
- [x] S10c "Günün hareketlileri ve anomaliler" — isteğe bağlı (`piyasa/hareket.html`, soru "Bugün piyasada neler oldu?"): a) evren config'i (BIST 100, research-data ABD listesi, en büyük ~30 kripto; likidite tabanı); b) pazar başına en çok yükselen/düşen 5 (% değişim, göreli hacim, endeks hareketi); c) kural tabanlı anomaliler (hacim ≥ 3× 20g ort., açılış boşluğu ≥ ±%5 hisse / ±%8 kripto, hareket ≥ 3× ATR(14), 52 hafta zirve/dip, endeksine ters > 3 puan) + düz Türkçe gerekçe; d) "Neden?" sütunu: "haber eşleştirmesi bekleniyor"; `movers_news.json` şeması docs/'ta; neden uydurulmaz; e) haber dili, uyarı, veri tarihi; `data/site/movers.json` kendi adımı (zamanlama belgelenir).
- [x] B1 **Boran isteği (22 Kasım): üst piyasa bandı** — ana sayfada başlığın altında sabit (kaymayan) rakam bandı: gram altın, dolar/TL, gram gümüş, Brent petrol, BIST 100 ($), Bitcoin — son değer + 1 günlük değişim; altın/gümüş/petrole dokununca görünüm değişir (gram TL ⇄ ons $, Brent ⇄ WTI). Telefonda yana kaydırılır, geniş ekranda 3 sütun. Veri tl.json (`band` alanı; fetch_tl'e BZ=F, CL=F eklendi).
- [x] S13 **Boran isteği (22 Kasım): dil seçeneği (Türkçe / English)** — yabancı ziyaretçi için başlıkta "TR · EN" seçici. a) Sayfa metinleri için `piyasa/i18n.js` sözlüğü (statik metinler, etiketler, ay adları, sayı biçimi `en-US`); b) veriden gelen cümleler (kural cümleleri, soru-cevaplar, hafta/dünya özetleri) için build adımları her cümlenin İngilizce şablonunu da üretir (`sentence_en`, `answers_en`; sayılar yine koddan); c) seçim `?lang=en` + "bu cihazda hatırla" (localStorage, try/catch), `hreflang` etiketleri, `lang` niteliği; d) yontem/veri sayfalarının İngilizce sürümü (`en/` altında statik); e) yasak kelime listesi İngilizce için de (buy, sell, opportunity, cheap, target…). Testler.
- [x] B2 **Boran isteği (22 Kasım): Grafikte karşılaştır** — `piyasa/karsilastir.html`: 2–3 varlığı aynı grafikte (aralık başı = 100) ya da 1.÷2. oranı (ör. altın/gümüş oranı); aralık 1A/3A/6A/YB/1Y/2Y; hazır seçimler; paylaşılabilir bağlantı (`?a=&b=&c=&mod=&ara=`); sürükle/tekerlek/iki parmakla yakınlaştır. Veri `fetch_tl.py` → `data/site/compare.json` (~2 yıl günlük; BIST 100 ve fonlar yalnız 100'e endeksli). Ana sayfada "Grafik" bölümü ve banttan bağlantı. Türkçe/İngilizce.
- [x] B3 **Boran isteği (22 Kasım): Günün özeti** — ayrı zamanlanmış Claude görevi her sabah (~09:45 İstanbul) izinli kaynaklardan en çok 8 haberi kendi cümleleriyle 2–3 cümlede özetler (TR + EN, kaynak bağlantısı, yorum/tavsiye yok) → data-feed `data/site/ozet.json` + `ozet/YYYY-MM-DD.json`; push öncesi `tools/check_ozet.py`. Ana sayfada "Günün özeti" bölümü (`piyasa/ozet.js`; 2 günden eskiyse gizli). Şema: `docs/OZET_SCHEMA.md`.
- [x] S13b-1 İngilizce ikinci aşama (1. kısım): `hesapla.html` ve `arsiv.html` tam İngilizce — sayfa betikleri `?lang=en`de cümleleri doğrudan İngilizce üretir (sayılar `en-US`, girişte `1,234.56` da okunur), statik metinler yalnız bu sayfalarda yüklenen `piyasa/i18n-pages.js` sözlüğünden (`PHD_I18N.add`; ana sayfa hafif kalır). Arşivde tarih bağlantıları `lang=en`i korur.
- [x] S13b-2 İngilizce ikinci aşama (2. kısım): hafta.html, dunya.html ve yontem.html'in tam İngilizcesi (bugün bu sayfalarda "yalnız Türkçe" notu var; sayı/tarih biçimi İngilizce); hafta/dunya build'lerinin `_en` cümleleri; arşivdeki eski günler için İngilizce cümle yok (yeniden yazılmaz, yalnız yeni günler).
- [x] S11 İzleyicisiz ölçüm: config.js'ten beslenen google-site-verification (ve Bing) meta yer tutucusu; DEPLOY_PLAN.md'de Search Console ve (A seçilirse) Cloudflare çerezsiz Web Analytics rehberi. Üçüncü taraf analitik yok.
- [x] S12 PARK — gelir modeli (yalnız gerçek kitle olunca; kod/cüzdan/hesap yok): `docs/MONETIZATION_PLAN.md` — (1) Türkiye pazarı türetilmiş verinin ücretli API katmanı, (2) x402 / Cloudflare Monetization Gateway (insanlar ve arama motorları ücretsiz), (3) önkoşullar: özel motor, Yahoo/FRED-kısıtlı girdilerin lisanslı kaynaklarla değişimi, alan adı, Cloudflare, Türkiye'de hukuki/vergi kontrolü (SPK, MASAK, kripto varlık kanunu) — sermaye piyasası avukatıyla. Riskler ve yeniden bakma tetikleyicileri.

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
  — `piyasa/vendor/` altında kendi sunucumuzdan (npm dosyası, Apache-2.0 + NOTICE), tembel yükleme (S5).
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
- **Dizine ekleme (S6):** `noindex` kaldırıldı; her sayfada canonical, OG/Twitter, JSON-LD
  (ana sayfa: WebSite + Dataset; arşiv: Dataset). `robots.txt` yalnız alan adının kökünde
  geçerli olduğu için GitHub Pages önizlemesinde (`/sweeplab/piyasa/`) etkisiz; son
  barındırıcıda (A/C) kökte çalışır. Arama + yapay zekâ tarayıcılarına izin verir.
- **Statik anlık görüntü (S6):** `tools/build_static.py` deploy işlerinde (A/C) çalışır:
  index.html/arsiv.html'deki `<!--S:…-->` yuvalarını bugünün verisiyle doldurur, Ekim
  2026'dan itibaren her gün için betiksiz `arsiv/YYYY-MM-DD.html` üretir, sitemap.xml'i
  günlerle yeniden yazar. `SITE_BASE` (repo değişkeni) ayarlanınca canonical/sitemap
  yeni alan adını izler. GitHub Pages önizlemesinde (main'e günlük commit yok) yalnız
  JS görünümü var.
- **Sicil kontrolü (S6):** KIRMIZI'ya geçiş + 20 gün içinde Nasdaq Bileşik ≥ %5 düşüş →
  "teyit edildi", yoksa "yanlış alarm"; KIRMIZI yokken 20 günde ≥ %10 düşüş → "kaçırılan
  düşüş". Nasdaq değeri yayımlanmaz (lisanslı), yalnız sonuç kelimesi. `sicil.json`
  yalnız ekleme: kesinleşmiş sonuç yeniden yazılmaz. Canlı sicil 21 Kasım sonrası;
  Ekim'den itibaren geriye dönük ayrı ve "bilgi amaçlı".
- **Kural girdisi:** `notebook_daily.json` 60 günlük pencere tutuyor; bu yüzden
  `history.csv` ve `archive/` yalnız ekleme yapılan ayrı dosyalar (HISTORY kuralı).

- **Dünya (S10b):** `tools/build_dunya.py` + tarihli sabit evren `tools/dunya_config.json`
  (2026-11-22; üç ayda bir gözden geçirme). Ham kapanışlar data-feed `data/research/world_1d/`
  (özel taraf); yayımlanan yalnız `data/site/dunya.json`: endeks/fon/emtia için yuvarlanmış
  seviye, % değişimler, 0/1 ortalama işaretleri, 200 güne % uzaklık; **şirketlerde fiyat yok**.
  Workflow ~06:00 UTC'de Asya seansları açıkken çalıştığı için **bugün tarihli çubuklar atılır**
  (yarım gün değeri yayımlanmaz) — tablolar son tamamlanmış seansı gösterir. Başlıklar: yalnız
  başlık + kaynak + saat + https bağlantı; DTD'li akış reddedilir, en çok 2 MB, en çok 10 başlık /
  akış başına 3 / son 4 gün. Akışlar: Korea.net (bilim-teknoloji, iş dünyası), gov.br ekonomi
  (CC BY-ND 3.0 → türev yok, yalnız başlık), Agência Brasil ekonomi, EIA Today in Energy (kamu
  malı), Samsung Newsroom. Çin ve Japonya için şartları uygun resmî akış seçilmedi (boş + not).
  **Midas:** resmî RSS/API bulunamadı, site "Tüm hakları saklıdır" → eklenmedi (⏸ Boran).
  `dunya.json` "yalnızca görüntüleme" (Yahoo kişisel kullanım + endeks sağlayıcı lisansları).

## Güvenlik kontrol listesi

- [x] `piyasa/` ve `data/site/` içinde sır/token/API anahtarı yok (her push öncesi tarama)
- [x] Workflow'da en az yetki: deploy işleri `contents: read`; sırrı yoksa iş atlanır
- [x] Loglara sır yazdırılmıyor (deploy adımları token'ı yalnız env üzerinden kullanır)
- [x] CSP `<meta http-equiv>` (self + tam CDN hostu; unsafe-eval yok, satır içi stil/script yok), referrer-policy — index.html + yontem.html (S3)
- [x] CDN varlığı yok: grafik kütüphanesi sabit sürümle (4.1.3) kendi sunucumuzdan; CDN eklenirse SRI zorunlu
- [x] Çekilen JSON / haber / kullanıcı girdisi yalnız textContent/DOM API ile (app.js'te innerHTML yok); dış bağlantılar `rel="noopener noreferrer"` (S3; sonraki sayfalarda da korunacak)
- [x] Üçüncü taraf izleyici/analitik yok, çerez yok
- [x] S7 Telegram: token yalnız env'den, hata mesajında URL yok; kanal kimliği sırrı yoksa adım atlanır
- [x] S8 config.js: bağlantılar yalnız `https://` ise ve textContent/DOM API ile; `rel="noopener noreferrer"`
- [x] S13 i18n.js: çeviri yalnız nodeValue/setAttribute ile (HTML ayrıştırma yok), dil tercihi yalnız `?lang=en` bağlantısında (çerez/depolama yok); yontem.html CSP `script-src 'self'` oldu (dil seçici için); S11 doğrulama kodu sıkı biçim kontrolüyle statik meta olarak yazılır
- [x] S9/S10 sayfaları (konum.html, veri.html) aynı CSP; konum.js yalnız textContent/DOM API; veri.html betiksiz içerik
- [x] S10b sayfaları (dunya.html, ana sayfa geniş ekran sütunu `dunya-side.js`) aynı CSP; yalnız textContent/DOM API; başlık bağlantıları yalnız `https://` + `rel="noopener noreferrer"`; RSS ayrıştırıcı DTD/varlık reddeder, boyut sınırı var
- [x] S6 sayfaları (arsiv.html, statik `arsiv/*.html`) aynı CSP; statik sayfalarda `script-src 'none'`; statik üretici tüm veri metnini `html.escape` ile yazar (testli)
- [x] S13b-1: `i18n-pages.js` yalnız tam eşleşme sözlüğü (HTML ayrıştırma yok); betiklerin İngilizce ürettiği düğümler `data-noi18n` ile işaretli, i18n.js bu düğümlerin niteliklerine de dokunmaz (placeholder'daki İngilizce sayı bozulmaz); hesaplayıcı yine ağ çağrısı yapmaz

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
- **2026-11-21 (3. çalışma, Boran'ın isteğiyle elle)** — S4 tamam.
  `tools/fetch_tl.py`: Yahoo TRY=X, GC=F, SI=F, XU100.IS → data-feed
  `data/research/tl_1d/*.csv` (özel taraf; ilk çalışmada `range=max` ile
  backfill, sonra 1 yıl birleştirme); yayımlanan `data/site/tl.json` yalnız
  türetilmiş: gram altın/gümüş TL, dolar/TL, BIST 100 dolar bazında (100'e
  endekslenmiş seri, endeks seviyesi serisi yok), 1g/7g/30g/yılbaşı/200g ort.
  farkı, küçük grafik serisi (son 400 gün), hesaplayıcı için güncel fiyatlar
  (BIST 100 yalnız güncel yuvarlanmış seviye; BTC/ETH notebook'tan). Kendi
  hata-toleranslı workflow adımı; sembol başına hata ayrı loglanır.
  Ana sayfada "TL tarafı" bölümü (SVG küçük grafik: siyah kapanış, kırmızı 200g
  ort.) + `piyasa/hesapla.html` (tamamen istemci tarafı; tek istek herkese açık
  tl.json; çerez yok; localStorage yalnız "Bu cihazda hatırla" işaretliyken,
  try/catch; Playwright ile doğrulandı). Testler: `tests/hesapla_test.js`
  (102 TL/gr gümüş → USDTRY 50,58'de ≈ $62,7, 60'ta ≈ $52,9) +
  `tests/test_fetch_tl.py`; toplam 41 test geçti. **Doğrulanmadı:** Yahoo bu
  ortamdan erişilemedi; semboller ilk Actions çalışmasında doğrulanacak
  (XU100.IS gecikmeli olabilir). Kaynak şart riski: Yahoo kişisel kullanım —
  gelir modelinden önce lisanslı/kamu kaynağıyla değiştirilecek (yontem.html
  ve tl.json `note` alanında yazılı). S4 ekran görüntüleri sentetik örnek
  veriyle alındı.
- **2026-11-21 (4. çalışma, Boran'ın isteğiyle elle)** — S4-fix + S5 tamam.
  Yahoo `range=max` aylık bar döndürdüğü için yayındaki tl.json değişimleri
  yanlıştı (ör. gram gümüş "200g ort. farkı +%460"); günlük geçmiş artık
  period1/period2 ile, depo kendini onarıyor. S5: `tools/build_charts.py` →
  `data/site/charts.json` (BTC/ETH son 365 gün kapanış + 50/200g ort., OKX
  günlük + varsa research mumları; makro geçmiş: ham skor, seviye, mod, sürüm
  sınırları), kendi hata-toleranslı adımı. `piyasa/charts.js`: grafik yalnız
  ilgili cevap açılınca yüklenir (kütüphane + JSON tembel yükleme); BTC/ETH
  cevabında iki çizgi grafik (siyah kapanış, gri 50g, kırmızı 200g), "Bugün
  makro hava" cevabında skor geçmişi (gri geriye dönük, siyah canlı, kırmızı
  canlı KIRMIZI; sürüm ve "canlı" başlangıç işaretleri). Kütüphane cdnjs
  yerine `piyasa/vendor/` altında kendi sunucumuzdan (aynı 4.1.3 npm dosyası;
  Apache-2.0 lisansı + NOTICE; sayfada TradingView bağlantılı atıf) → CSP
  `script-src 'self'` kalır, SRI gerekmez (cdnjs bu ortamdan erişilemedi).
  46 test geçti. Boran'ın iki fikri S6 ve S10b'ye eklendi.
- **2026-11-21 (5. çalışma, Boran'ın isteği: "Ekim'den beri tuttuğumuz veriyi
  de ekle")** — `tools/backfill_site_history.py`: data-feed'deki
  `notebook_daily.json` git geçmişinden (8 Ekim'den beri 120 sürüm)
  geriye dönük doldurma. history.csv 2026-09-22'de başlıyordu; **2026-08-30 ..
  2026-09-21 (23 gün)** eklendi (tam 20 günlük karşılaştırması olan en eski
  günler; mode=retro; mevcut satırlar bayt bayt korunarak ÖNE eklendi; arşiv
  dosyaları yalnız eksikse yazıldı). Ayrıca `data/site/retro_pit.csv`: 7 Ekim –
  20 Kasım arasındaki 45 gün, **o sabahki veriyle** (point-in-time) puanlandı.
  Bulgu: 45 günün 16'sında o sabahki ham skor, sonradan (düzeltilmiş veriyle)
  hesaplanan history.csv skorundan farklı (ör. 16 Ekim: o sabah 3, sonradan 5)
  — veri revizyonları/haftalık serilerin taşınması yüzünden. history.csv
  değiştirilmedi (kural: yayımlanmış satır yeniden yazılmaz); karar Boran'da:
  retro satırları point-in-time değerlere çevirmek tek seferlik, belgelenmiş
  bir düzeltme olarak yapılabilir. S6 "Sicil" bu farkı açıkça gösterecek.
  Hesaplayıcı da sadeleşti (soru biçiminde etiketler, düz Türkçe özet, birim
  uyarısı, dolar için anlamsız başabaş sütunu kaldırıldı). 47 test geçti.
- **2026-11-21 (6. çalışma, Boran: "hangisi doğruysa onu paylaş, hatayı bul")** —
  Hata bulundu ve düzeltildi. (1) Sabah derlemesinin en yeni satırı bir önceki
  günün ABD verisini taşıyor (FRED bir gün geç); bu "tamamlanmamış" gün
  puanlanıyordu → `build_site.settled()`: yalnız girdileri o güne ait gün
  puanlanır (ABD tatilleri için sonraki satır kontrolü). (2) Geriye dönük
  pencerenin ilk 20 günü kısaltılmış karşılaştırmayla hesaplanmıştı → saklanan
  eski sürümlerden tam 20 günlük karşılaştırma. data-feed'de belgelenmiş
  düzeltme: history.csv 2026-08-30..2026-11-19 (82 gün) yeniden kuruldu,
  11 kayıt düzeltildi (arşivde `duzeltme` + önceki değer), 2026-11-20 kaldırıldı,
  yanıltıcı `retro_pit.csv` silindi. `MAKRO_KURALLAR_v1.md`'ye "veri günü"
  netleştirmesi eklendi (eşikler aynı). `backfill_site_history.py --rebuild`
  canlı satır varsa çalışmayı reddeder. 51 test geçti.
  **Önemli:** PR birleşmeden main'deki eski build_site.py yarın sabah
  tamamlanmamış 20–21 Kasım satırlarını yeniden ekler → PR sabah 05:50 UTC'den
  önce birleşmeli.
- **2026-11-21 (7. çalışma, Boran'ın isteği)** — Kural başlıklarına ve TL
  kalemlerine tıklayınca açılan açıklama: "Nedir? / Neden izleniyor? / Nasıl
  hesaplanıyor? / Kaynak" + verinin tarihi ve karşılaştırma günü (yalnız
  yontem.html'de zaten yazan eşikler; DOM API, `aria-expanded`). Etiket
  düzeltmesi: veri Nasdaq **Bileşik** (FRED NASDAQCOM), "Nasdaq 100" yazıyordu
  (build_site, yontem.html; yeni kayıtlardan itibaren).
- **2026-11-21 (8. çalışma, Boran'ın isteği)** — Piyasa verisinde 1 yıl geriye:
  `fetch_tl.py` her kalem için "1 yıl önce" değeri + değişimi (`val_1y`,
  `date_1y`, `chg_1y`), küçük grafikler son 1 yılı gösteriyor (seri 400 takvim
  günü), BTC ve ETH (Yahoo BTC-USD/ETH-USD) TL tarafı listesine eklendi
  (hesaplayıcı yine OKX kapanışını tercih eder). Kendi ölçümümüz (makro hava)
  grafikte **Ekim 2026'dan** itibaren gösteriliyor (`build_charts.MACRO_FROM`);
  history.csv'deki Ağustos–Eylül retro satırları silinmedi (yalnız gösterilmiyor;
  S6 arşiv/sicil de Ekim'den başlayacak). "Veri: 20 Kasım" doğru: 21 Kasım
  cumartesi, son kapanış cuma.
- **2026-11-21 (9. çalışma, Boran'ın soruları)** — Kural cümleleri sadeleşti:
  "eşik aşıldı/aşılmadı" yerine eşik kelimeyle ("%3'ten fazla düştü",
  "0,25 puanlık eşiğe ulaşmadı"); kuralların üstüne "kırmızı nokta = bugün işaret
  var" açıklaması. Bağlam (puanı etkilemez): stablecoin 7 günün yanında 20 günlük
  değişim; petrolde karşılaştırma günü 60 günlük zirveye yakınsa "önceki ani
  yükselişin geri alınması olabilir" notu; "talep zayıflığı" artık "olası" bir
  yorum olarak yazılıyor. **Karar bekleyen:** `docs/MAKRO_KURALLAR_v1_1_ONERI.md`
  (P1 düşüş kolu için kredi teyidi ≥ 0,25; etkisi: 18–19 Kasım 7→6, seviye aynı).
  ⏸ Boran onaylarsa v1.1.
- **2026-11-21 (Boran isteği)** — S6b "Dünyada bu Pazartesi / Cuma" eklendi
  ve denendi (23 Kasım pazartesi ve 20 Kasım cuma baskısı yerelde üretildi;
  ekran görüntüleri `docs/site-preview/s6b-*.png`). `tools/tarihte.json` 10
  kaynaklı girdiyle başladı. SPY/QQQ şimdilik 5 yıllık (research us_1d) —
  fetch_tl 2000'den beri geçmişi ilk çalışmada çekecek. 62 test geçti.
- **2026-11-21 (zamanlanmış çalışma)** — S6 tamam. `piyasa/arsiv.html` (Ekim 2026'dan
  günler: seviye, skor, 9 kural noktası, sürüm, geriye dönük/canlı; tarih → o günün
  kaydı) + "Sicil" (`tools/build_sicil.py` → `data/site/sicil.json`, kendi
  hata-toleranslı adımı; yanlış alarmlar ve kaçırılan düşüşler dahil; kontrol
  yontem.html#sicil'de). Ana sayfada **"Tarih seç"** (Boran isteği): `archive/
  YYYY-MM-DD.json` aynı düzende, yeniden hesaplanmadan; `?tarih=` bağlantısı,
  "Bugüne dön". SEO: canonical, OG/Twitter, JSON-LD, sitemap.xml, robots.txt, favicon,
  başlık sırası düzeltmesi (TL kalemleri h2). Statik görüntü: `tools/build_static.py`
  (deploy işlerinde). **Lighthouse mobil** (yerel, data-feed verisiyle): ana sayfa
  perf 99 / a11y 100 / best 100 / SEO 100; arşiv 95/100/100/100; hesapla 98/100/100/100;
  yöntem 96/100/100/100; hafta 98/100/96/100 (yerelde hafta.json yok → konsol 404);
  statik gün sayfası 100/100/100/100. Geriye dönük sicil (Ekim'den): 5 KIRMIZI
  geçişinin 5'i teyit (bilgi amaçlı; canlı değil). 67 Python testi + hesapla testi geçti.
  **Kalan:** S6b'nin her çalışma görevi (önümüzdeki iki haftaya kaynaklı 3–6 "Tarihte
  bu hafta" + 1 "ilk") bu çalışmada yapılmadı — kaynak doğrulaması için sonraki
  çalışmaya bırakıldı. Mobilde arşiv tablosunun "Kayıt" sütunu yatay kaydırmayla görünür.
- **2026-11-21 (zamanlanmış çalışma)** — S7 + S8 tamam. `site-dev` uzak depoda yoktu (PR #46
  birleşip dal silinmiş) → main'den (`3092a97`) yeniden açıldı. S7: `tools/post_public.py`
  + 4 test (seviye değişimi yalnız canlı satırda, Pazar özeti, sırrı yoksa atlama, çift
  gönderim yok, yasak kelime yok). ⏸ Boran: kanal + bot yöneticisi + `TELEGRAM_PUBLIC_CHANNEL_ID`.
  S8: `piyasa/config.js`, slogan başlıkta, Altınkulak altbilgide; `tools/build_og.py` günün
  kartı (Pillow workflow'da kuruluyor; olmazsa sabit kart) + 3 test. build_static og:image
  adresini son barındırıcıya çeviriyor (denendi). 74 Python testi + hesapla testi geçti.
  Ekran görüntüleri: `docs/site-preview/s8-*.png`, kart: `piyasa/og.png`.
  **Kalan:** S6b'nin "Tarihte bu hafta" kaynaklı girdi görevi bu çalışmada da yapılmadı
  (kaynak doğrulaması gerekiyor). Sıradaki: S9 (research verisi 13 Kasım sonrası satır
  koşulu kontrol edilecek), S10.
- **2026-11-22 (zamanlanmış çalışma)** — S9 + S10 tamam. Koşul sağlandı: research
  `us_1d` son satır 19 Kasım, `candles_1d` 20 Kasım (> 13 Kasım). S9: `tools/build_konum.py`
  + sabit, tarihli evren `tools/konum_universe.json` (Türkiye: BIST 100 TL ve dolar
  bazında, gram altın, gram gümüş, dolar/TL; SPY, QQQ, RSP, SMH; GLD, SLV; BTC, ETH;
  11 büyük ABD şirketi; BIST tekil hisse yok) → `data/site/konum.json`: yalnız 20/50/200
  gün ortalamasının üstü/altı (0/1) + 200 güne % uzaklık + tarih; fiyat seviyesi yok;
  grup içinde alfabetik; 7 günden eski satır "eski". `piyasa/konum.html` (ana sayfadan
  "Fiyatlar ortalamalarına göre nerede?"), yontem.html#konum notu, kendi hata-toleranslı
  workflow adımı. S10: `tools/build_catalog.py` → `data/site/index.json` (tüm uçlar,
  şema kimliği/sürümü, güncelleme saati, lisans sınıfı, var/yok; sabit yollar),
  `piyasa/veri.html` (Türkçe + kısa İngilizce: alanlar, saat, lisans, atıf, kararlılık
  kuralı), today.json'a `schema: phd.today/1` + `license_note`. **Lisans netleştirmesi:**
  Yahoo/OKX türevli dosyalar (tl.json, konum.json, hafta.json, charts.json kripto kısmı)
  artık "yalnızca görüntüleme" olarak etiketleniyor (önceden "CC BY 4.0" yazıyordu;
  girdi şartlarıyla çelişiyordu). sitemap + build_static'e konum.html/veri.html eklendi.
  84 Python testi + hesapla testi geçti. Ekran görüntüleri `docs/site-preview/s9-*`,
  `s10-*` (data-feed'in gerçek verisiyle yerel). **Açık konu:** `history.csv` satır
  içinde kaynak alanı taşımıyor (yalnız `rules_version`, `generated_at`); yalnız-ekleme
  dosyayı bozmamak için kaynak/lisans/atıf `index.json` + veri.html'de veriliyor —
  istenirse ayrı `history.meta.json` eklenebilir. **Kalan:** S6b'nin "Tarihte bu hafta"
  kaynaklı girdi görevi bu çalışmada da yapılmadı (kaynak doğrulaması gerekiyor).
  Sıradaki: S10b (Dünya), S10c.
- **2026-11-22 (zamanlanmış çalışma, 2.)** — S10b tamam. `tools/build_dunya.py` (kendi
  hata-toleranslı workflow adımı; `world_1d` "Store data" adımına eklendi) + 16 test;
  `piyasa/dunya.html` + `dunya.js` (ana sayfada "Dünyada durum ne?" bağlantısı, JSON yalnız
  sayfa açılınca), ana sayfada ≥ 1200 px sağ sütun (`dunya-side.js`: bölge endekslerinin son
  günlük değişimi + ilk 5 başlık; telefonda yüklenmez). yontem.html#dunya, veri.html#dunya,
  index.json kaydı ("her gün"), sitemap, build_static sayfa listesi, ana sayfa JSON-LD.
  100 Python testi + hesapla testi geçti. **Doğrulanamadı:** bu ortamdan Yahoo ve RSS
  adreslerine erişim yok → semboller (özellikle `^TOPX`, `000300.SS`, `^HSTECH` — isteğe
  bağlı, yoksa tablodan düşer) ve akışlar ilk Actions çalışmasında doğrulanacak; sonuç
  `dunya.json → missing` ve `basliklar.kaynaklar[].durum` alanlarında ve adım logunda.
  Ekran görüntüleri (`docs/site-preview/s10b-*`) **örnek veriyle** (sayfada "Önizleme: örnek
  veri" uyarısı görünür; altın/gümüş gerçek tl_1d verisi). Lighthouse bu çalışmada ölçülmedi.
  **Kalan:** S6b "Tarihte bu hafta" kaynaklı girdi görevi; Midas izni (Boran). Sıradaki: S10c.
- **2026-11-22 (Boran ile canlı)** — Altınkulak bağlantısı gizlendi (config.js `deeper.url` boş;
  Altınkulak doğrulanınca geri yazılacak). B1 üst piyasa bandı yapıldı (ekran görüntüleri
  `docs/site-preview/band-home-390.png`, `band-home-1440.png`; petrol ve ons değerleri ilk Actions
  çalışmasında gelir — önizlemede petrol örnek değerle). Boran'ın dil seçeneği isteği S13 olarak eklendi.
  Sol boşluk bilerek boş bırakıldı (Boran: üst band yeterli).
- **2026-11-22 (Boran ile canlı, 2.)** — S10c tamam. `tools/build_movers.py` + `tools/movers_config.json`
  (tarihli sabit evren: 44 büyük/likit BIST hissesi — resmî BIST 100 bileşimi değil, Actions'ta
  Yahoo `.IS` ile çekilir, `data/research/bist_1d/` özel tarafta; ABD araştırma listesi fonlar hariç;
  OKX ~30 coin) → `data/site/movers.json`: pazar başına endeksin 1g hareketi, en çok yükselen/düşen 5
  (yüzde + göreli hacim), kural tabanlı anomaliler (hacim ≥ 3×, açılış boşluğu ±%5 / ±%8, ≥ 3× ATR(14),
  52 hafta zirve/dip, endeksine ters > 3 puan) düz Türkçe gerekçeyle; fiyat yok; likidite tabanı
  (20g ort. işlem hacmi BIST 250 mn TL, ABD 200 mn $ + 5 $ alt fiyat); bugünün tamamlanmamış mumu ve
  güncellenmeyen isimler dışarıda. "Neden?" asla yazılmaz: `docs/MOVERS_NEWS_SCHEMA.md` şemasıyla ayrı
  görev `movers_news.json` üretirse sayfa birleştirir. `piyasa/hareket.html` (ana sayfada "Bugün
  piyasada neler oldu?"), yontem.html#hareket, veri.html#movers, index.json kaydı, sitemap. Kendi
  hata-toleranslı adımı (zamanlama: daily-brief ~06:00 UTC — BIST/ABD seansları ve kripto UTC günü
  kapanmış). 6 yeni test; 107 Python testi geçti. Ekran görüntüleri `docs/site-preview/s10c-*`
  (gerçek data-feed verisiyle; BIST bu ortamdan çekilemedi → ilk Actions çalışmasında doğrulanacak).
- **2026-11-22 (Boran ile canlı, 3.)** — S13 (ilk aşama), S11, S12 tamam.
  **S13:** `piyasa/i18n.js` her sayfada ilk betik: Türkçe varsayılan, `?lang=en` ile İngilizce
  (çerez/depolama yok; seçim bağlantıyla taşınır, iç bağlantılar `lang=en`'i korur), başlıkta
  "EN/TR" bağlantısı, `hreflang` etiketleri. Statik ve sonradan yazılan metinler sözlük + kalıp
  cümleler + Türkçe→İngilizce sayı/tarih biçimiyle çevrilir. `build_site.py` artık her kural için
  `title_en`, `group_en`, `sentence_en`, ayrıca `headline_en`, `level_en`, `held_note_en`,
  `answers_en` üretir (aynı sayılar, koddan; testte Türkçe cümledeki her sayının İngilizcede de
  olduğu ve yasak kelime olmadığı denetlenir). Ana sayfa, Konum ve Hareket tamamen İngilizce;
  diğer sayfalarda "yalnız Türkçe" notu (S13b). Ekran görüntüleri `docs/site-preview/s13-*`.
  **S11:** `config.js → verification` + `build_static.verification_meta()` (deploy sırasında ana
  sayfaya statik meta; değer biçimi doğrulanır) + DEPLOY_PLAN.md'de Search Console / Bing / Cloudflare
  rehberi (Cloudflare Web Analytics CSP istisnası gerektirdiği için Boran'ın kararı).
  **S12:** `docs/MONETIZATION_PLAN.md` (park). Testler: 109 Python + hesapla + i18n.
  Kalan: S13b, S6b "Tarihte bu hafta" kaynaklı girdi görevi, ⏸ Boran adımları.
- **2026-11-22 (Boran ile canlı, 4.)** — B2 Grafikte karşılaştır yapıldı (ekran görüntüleri
  `docs/site-preview/cmp-*`; gerçek data-feed tl_1d verisiyle, Brent/WTI ilk Actions çalışmasında gelir).
  `compare.json` tl.json'u hiçbir durumda bozmayacak şekilde ayrı try içinde yazılır. 110 Python testi geçti.
- **2026-11-22 (Boran isteği)** — SweepLab terminali kökten ayrıldı: `index.html` → `terminal/index.html`
  (göreli yollar `../strategies/`, `../data/market/`; `noindex`), kök `index.html` artık
  `piyasa/`'ya yönlendiriyor (`noindex`, canonical piyasa). Terminal adresi:
  https://samiboran.github.io/sweeplab/terminal/ — panel/, bot/ etkilenmedi.
- **2026-11-22 (zamanlanmış çalışma)** — S13b iki parçaya bölündü; S13b-1 tamam (hesapla + arşiv tam
  İngilizce). `tests/i18n_test.js` genişledi (sayfa sözlüğü yalnız İngilizce modda, çekirdek sözlüğü
  ezmez; i18n-pages/hesapla/arsiv'de eylem kelimesi yok). Playwright ile 5 varlık × İngilizce tarandı:
  sayfada Türkçe metin kalmadı (yalnız `<noscript>`). Ekran görüntüleri `docs/site-preview/s13b-*`
  (gerçek data-feed verisiyle). S6b her çalışma görevi: `tools/tarihte.json`'a kaynaklı 3 gün girdisi
  (28 Kasım 2010 İrlanda AB–IMF programı — IMF; 30 Kasım 2011 merkez bankalarının ortak dolar swap
  adımı — Fed; 30 Kasım 2015 yuan SDR sepetinde — IMF) + 1 "ilk" (1866 Dersaadet Tahvilat Borsası —
  Borsa İstanbul) eklendi; 23 Kasım–6 Aralık aralığında artık 10 gün girdisi var. 114 Python testi +
  hesapla + i18n testleri geçti. Not: kök terminalin `terminal/`'e taşınması Boran'ın isteğiydi (bu
  PR'da); zamanlanmış görevdeki "kök index.html terminali" kuralı bu karar için güncellenmeli.
  Sıradaki: S13b-2.
- **2026-11-22 (Boran ile canlı, 5.)** — S13b-2 tamam: site baştan sona Türkçe/İngilizce.
  `build_week.py` İngilizce cümleler (`sentence_en`, `this_week_sentence_en`, `title_en`, `headline_en`,
  `week_label_en`, `method_en`, takvim `name_en`), `tarihte.json` girdilerine `title_en/text_en/topic_en`
  (14 girdi çevrildi; yeni girdilerde zorunlu, `_doc`'ta yazılı). `hafta.js` İngilizce alanları kullanır.
  Dünya sayfası `i18n-pages.js` sözlüğü + kalıp/ifade kurallarıyla (`PHD_I18N.add(dict, patterns, phrases)`).
  `yontem.html` iki dilli bloklar (`data-lang="tr|en"`; `#k1` → `#en-k1`). `veri.html` Türkçe + mevcut
  İngilizce bölüm (notta belirtiliyor). Mobil arşivde 5 px yatay taşma düzeltildi (`.tablewrap{position:relative}`).
  Haber başlıkları kaynağın kendi dilinde kalır. Bütün maddeler tamam → zamanlanmış inşa görevi kapatılabilir.
- **2026-11-22 (Boran ile canlı, 6.)** — İnşa bitti; zamanlanmış inşa görevi kapatılıyor. Süren işler:
  günlük veri + Pazartesi/Cuma baskıları GitHub Actions'ta (daily-brief) değişmeden çalışır; "Günün özeti"
  ayrı görevle her sabah. "Tarihte bu hafta" kaynaklı girdileri artık özet görevi her perşembe
  data-feed `data/research/tarihte_extra.json` dosyasına ekler (PR gerekmez; `build_week.load_extra`:
  kaynaksız / https olmayan / tekrar eden girdi atlanır). Telegram kanalı ve X paylaşımı: site adı ve alan
  adı belli olunca (Boran kararı).
- **2026-11-22 (zamanlanmış çalışma, kontrol)** — Bütün maddeler işaretli; çelişki taraması temiz (yasak kelime yok, `piyasa/`'da puanlama kodu yok, HY OAS yalnız yön kelimesi). Yapılacak iş kalmadı — zamanlanmış inşa görevi devre dışı bırakılabilir.
- **2026-11-22 (Boran ile canlı, 7.)** — Geri bildirim bağlantısı: altbilgide "Öneri ve hata bildir" (`config.js` → `feedback.email`; boşsa görünmez). Yalnız `mailto:` açar (form, izleyici, çerez yok), konu + sayfa yolu hazır gelir, TR/EN. Adres Boran'ın site için açacağı e-posta — ⏸ Boran.
- **2026-11-22 (Boran ile canlı, 8.)** — B4 gün içi yenileme (Boran isteği: saatlik değil, kritik saatler): yeni `.github/workflows/intraday.yml` hafta içi 10:30 ve 18:30 İstanbul + `research-data` bitince (~01:30) yalnız `fetch_tl.py` (üst bant, tl/compare.json) ve `build_movers.py` çalıştırır; makro seviye, dünya, hafta ve Telegram 09:00'da kalır. `build_movers.cutoff`: o günün çubuğu yalnız seans kapanınca kullanılır (`closed_after_utc`: BIST 15:20, ABD 21:10 UTC; kripto hiç) — testli. Bant notu "22 Kas 18:30 itibarıyla (~15 dk gecikmeli)" (TR/EN). Deploy işleri yeniden kullanılabilir `site-deploy.yml`'ye taşındı (daily-brief + intraday çağırır; sırrı yoksa atlanır). daily-brief data-feed push'u artık `pull --rebase` + 3 deneme. veri.html/yontem.html saatleri güncellendi. `intraday.yml` main'e birleşince çalışmaya başlar (`workflow_run` yalnız varsayılan dalda tetiklenir).
- **2026-11-22 (Boran ile canlı, 9.)** — Dış değerlendirmeden (Opus + Sonnet) düzeltmeler: "İstatistik yalan söylemez" sloganı kaldırıldı (tüm sayfalar, config.js boş → gizli; og kartında yerine "Yatırım tavsiyesi değildir"). Mobil bant yatay kaydırma yerine 2 sütunlu ızgara (değerler kesilmiyor). Üst menüye "Hesapla" eklendi (tüm sayfalar, TR/EN). Ana sayfada seviyenin altına çerçeve cümlesi: seviye ne söyler/ne söylemez, yanlış alarm → Sicil bağlantısı, ABD verisinin bir iş günü gecikmesi. Eski önizleme görüntüleri (62 adet, bazıları "Yapım aşamasında"/örnek veri) silindi; güncel set gerçek data-feed verisiyle yeniden alındı. Kontrol edilenler: tarih seçici tr-TR'de gg.aa.yyyy (yanlış alarm — İngilizce tarayıcıdan); "Nasdaq 100" metni yalnız 21 Kasım'da üretilmiş today.json'da, kod zaten "Nasdaq Bileşik" yazıyor (bir sonraki iş günü düzelir, arşiv kayıtları yeniden yazılmaz).
- **2026-11-22 (Boran ile canlı, 10.)** — Dış değerlendirmenin 6 önerisi (Boran onayı): (1) ana sayfa sırası: bant → TL tarafı (hesaplayıcı bağlantısı en üstte) → Günün özeti → Makro hava + kurallar → Sorular → "Daha fazlası" (5 sayfa tek listede); (2) sicil etiketleri nötr: "düşüş geldi / düşüş gelmedi / KIRMIZI'sız düşüş" (sicil.json kodları aynı, yalnız görünen kelime; yontem/arsiv/statik özet TR+EN); (3) yontem.html "Eşikler neden bu değerler?" (ayarlanmadı, yuvarlak ve yaygın değerler, donduruldu) + history.csv'den seviye dağılımı (`yontem-stats.js`, CSP connect-src eklendi); (4) "Sorular" bölümünden kural listesini tekrarlayan soru çıkarıldı; (5) Türkiye bileşeni → `docs/MAKRO_KURALLAR_v2_TASLAK.md` (yürürlükte değil; ⏸ Boran: EVDS API anahtarı + eşik kararı); (6) Dünya/Hareket ana sayfada tek satıra indi. Not: Agência Brasil ekonomi akışından ekonomi dışı başlık (Mega-Sena) gelebiliyor — sonraki iş: başlık filtresi.
- **2026-11-22 (Boran ile canlı, 11.)** — İkinci dış değerlendirmeden (Opus + Sonnet, ikisi 6,5/10): (1) hesaplayıcıya isteğe bağlı "Makas / komisyon (%)" + "fiyatlardan hesapla" (satış/alış → %); sonuçta bozdurunca eline geçen, makas sonrası kâr/zarar, makas dahil başa baş fiyatı (testli). Referans: TCMB dolar efektif alış-satış farkı + kur tarihi (`fetch_tl.parse_tcmb`, today.xml, DTD reddedilir, hata olursa önceki değer korunur; testli) — altın/gümüş için serbest günlük makas verisi yok, sayfada yazıyor. (2) Bant tarihi: gram altının çubuğu bugünse saat, değilse "20 Kas kapanışı" (dolar hafta sonu kotasyonu "canlı" izlenimi veriyordu). (3) Bandın altında tek satır "Makro hava: KIRMIZI · 19 Kas ABD verisi · ne anlatıyor?". (4) Dar ekranda logo tek satır, menü alt satırda; gri metin #595959, etiketler 12 px. (5) Başlıklar: `dil` alanı, ana sayfa yan sütunu yalnız en/tr; ekonomi akışlarında piyango başlıkları ayıklanır (`exclude_words`); boş kimlikli EIA bağlantısı guid'den tamamlanır, tamamlanamazsa atlanır (testli). Bekleyen: TÜFE'ye göre reel getiri (EVDS anahtarı gerekir), KIRMIZI kelimesi (Boran düşünüyor).
- **2026-11-23 (Boran ile canlı, 12.)** — Veri kaynakları araştırıldı → `docs/VERI_KAYNAKLARI.md`. Karar (Boran): ücretsiz ve doğru kaynağı olan geçer, olmayan Yahoo'dan devam; gelir modeli ya da uyarı gelirse yeniden. Bugün hiçbir veri birebir değiştirilmedi: TCMB günde bir kez (gün içi gram altını bozar), EIA petrol haftalık gecikmeli; TCMB yalnız makas referansında. Üçüncü dış değerlendirme (ikisi yine 6,5/10) düzeltmeleri: hesaplayıcıda tek fiyat tarihi (gram altın kapanışı; hafta sonu dolar kotasyonu "22 Kasım" gösteriyordu), Türkçe binlik ayırıcı okunuyor ("5.800" → 5800; önce 5,8 sayılıyordu), makas örnekleri bugünkü fiyatın ±%1'i, sonuçta "yatırım tavsiyesi değildir" satırı, tutarlar tek satırda.
- **2026-11-23 (Boran ile canlı, 13.)** — Hesaplayıcı merkezde (Boran onayı): (1) ana sayfada "Senin pozisyonun · yalnız bu cihazda" kartı (`pozisyon.js`; yalnız "Bu cihazda hatırla" işaretliyse; güncel fiyatla K/Z, başa baş, makas dahil başa baş; "Düzenle" / "Bu cihazdan sil"); (2) "Farklı fiyatlardan birden çok alım" — en çok 20 satır, ağırlıklı ortalama maliyet ve toplam miktar alanlara yazılır (BIST'te gizli: miktar alanı TL tutarı); (3) "Diğer: çeyrek, cumhuriyet, bilezik… (fiyatı sen gir)" — gramdan türetilmez, bugünkü bozdurma fiyatını kullanıcı yazar; (4) kayıt v2: sayılar dilden bağımsız saklanır (TR'de kaydedilen değer EN'de doğru okunur; v1 kayıtlar okunmaya devam eder); (5) bant/hesaplayıcı/kartta "kapanışı" yerine "verisi" (vadeli altın pazar akşamı açılıyor; "kapanış" değil). Testler: `averageLots`, özel varlık. Bekleyen: TÜFE'ye göre reel getiri (EVDS anahtarı, Boran).
- **2026-11-23 (Boran ile canlı, 14.)** — Dördüncü dış değerlendirme (Sonnet 7/10, Opus 6,5/10). Düzeltilen: "Diğer" varlıkta kart, fiyatın girildiği tarihi gösterir (kayıtta `t`); ana sayfa önizlemesi yenilendi (kart varken üstteki hesaplayıcı bağlantısı gizli, çift çizgi yok — eleştiri eski görüntüdendi). Haftalık "EVDS anahtarı hatırlatması" zamanlanmış görevi kuruldu (pazartesi 10:35 İstanbul). Açık öneriler (Boran kararı): birden çok pozisyon (altın + dolar + çeyrek toplamı), makro hava satırını kartın altına/ayrı sayfaya almak, kayıt dışa/içe aktarma, alan adı ve "gram altın maliyet hesaplama" arama sayfası.
