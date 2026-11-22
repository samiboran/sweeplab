/* Piyasa Hava Durumu — English dictionary for the inner pages (S13b). Loaded right after i18n.js
   only on the pages that need it, so the home page stays light. Exact-match strings only. */
(function () {
  "use strict";
  var I = window.PHD_I18N;
  if (!I || !I.en) return;
  I.add({
    // hesapla.html
    "Benim pozisyonum ne durumda?": "How is my position doing?",
    "Güncel fiyatlar yükleniyor…": "Loading current prices…",
    "Girdiğin bilgiler cihazından çıkmaz. Hesap tarayıcında yapılır; hiçbir yere gönderilmez, çerez kullanılmaz.":
      "What you enter never leaves your device. The calculation runs in your browser; nothing is sent anywhere and no cookies are used.",
    "Varlık": "Asset", "Gram altın": "Gold (gram)", "Gram gümüş": "Silver (gram)", "Dolar": "Dollar",
    "BIST 100 (puan)": "BIST 100 (points)", "Maliyet para birimi": "Cost currency",
    "Ortalama maliyet (birim başına)": "Average cost (per unit)", "Miktar": "Amount",
    "Makas / komisyon (%) — isteğe bağlı": "Spread / commission (%) — optional",
    "örn. 2": "e.g. 2", "örn. 3000": "e.g. 3000", "örn. 2940": "e.g. 2940",
    "Kuyumcu, banka ya da aracı kurum alış ve satış fiyatını farklı verir; bozdururken eline geçen tutar piyasa fiyatından düşüktür. Kendi aldığın yerin makasını gir.":
      "Jewellers, banks and brokers quote two different prices; when you cash out, you receive less than the market price. Enter your own dealer's spread.",
    "Makası bilmiyor musun? Fiyatlardan hesapla": "Don't know the spread? Work it out from prices",
    "Satış fiyatı (senin ödediğin)": "Ask price (what you pay)",
    "Alış fiyatı (bozdurunca aldığın)": "Bid price (what you get when you cash out)",
    "Bu cihazda hatırla": "Remember on this device", "Hesapla": "Calculate",
    "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır. Hesap sonuçları yalnız aritmetiktir.":
      "Not investment advice. Data for information only. Results are plain arithmetic.",
    "Fiyat tarihi: —": "Price date: —",
    "örn. 102,50": "e.g. 102.50", "örn. 10": "e.g. 10",
    "Benim pozisyonum ne durumda? — Piyasa Hava Durumu": "How is my position doing? — Piyasa Hava Durumu",
    // arsiv.html
    "Arşiv ve sicil": "Archive and track record",
    "Arşiv ve sicil — Piyasa Hava Durumu": "Archive and track record — Piyasa Hava Durumu",
    "Her gün o sabah yayımlanan kayıt. Kayıtlar sonradan yeniden yazılmaz; belgelenmiş bir hata düzeltmesi olursa kaydın içinde yazılır.":
      "Each day's record as published that morning. Records are never rewritten later; a documented bug fix, if any, is noted inside the record.",
    "Sicil": "Track record",
    "KIRMIZI işaretlerinden sonra ne oldu?": "What happened after RED signals?",
    "Sicil yükleniyor…": "Loading track record…",
    "Kontrol: KIRMIZI'ya geçilen günden sonraki 20 gün içinde Nasdaq Bileşik, o günkü kapanışının en az %5 altında kapandıysa \"düşüş geldi\", kapanmadıysa \"düşüş gelmedi\" yazılır. Seviye KIRMIZI değilken 20 günde %10'luk düşüş olursa \"KIRMIZI'sız düşüş\" yazılır. Amaç geçmişi olduğu gibi göstermektir; gelecek hakkında bir şey söylemez.":
      "Check: if within 20 days of a switch to RED the Nasdaq Composite closed at least 5% below that day's close, the entry says \"fall followed\"; otherwise \"no fall followed\". A 10% drop within 20 days while the level was not RED is listed as \"fall without RED\". The aim is to show the past as it was; it says nothing about the future.",
    "Geriye dönük sicil (bilgi amaçlı, Ekim 2026'dan)": "Retro track record (for information, from October 2026)",
    "Bu günler kurallar donmadan önce, sonradan hesaplandı. Canlı sicile sayılmaz.":
      "These days were computed afterwards, before the rules were frozen. They do not count towards the live record.",
    "Günler": "Days",
    "Noktalar dokuz kuralı sırayla gösterir: Stablecoin arzı, Fed net likiditesi, Reel faiz, Dolar endeksi, Kredi risk primi, VIX, Nasdaq Bileşik, Altın ve dolar, Petrol. Dolu kırmızı: işaret var. Tarihe dokununca o günün sayfası açılır.":
      "The dots show the nine rules in order: Stablecoin supply, Fed net liquidity, Real yield, Dollar index, Credit risk premium, VIX, Nasdaq Composite, Gold and the dollar, Oil. Solid red: signal. Tap a date to open that day's page.",
    "Günlük makro hava kayıtları": "Daily macro weather records",
    "Tarih": "Date", "Seviye": "Level", "Skor": "Score", "Sürüm": "Version", "Kayıt": "Record",
    "Arşiv yükleniyor…": "Loading archive…",
    "(türetilmiş veri, CC BY 4.0)": "(derived data, CC BY 4.0)",
    "Kural sürümü v1 · Ağustos–Kasım 2026 kayıtları geriye dönük; 21 Kasım 2026'dan sonrası canlı.":
      "Rules v1 · August–November 2026 records are retro; from 21 November 2026 on they are live.",
    "Bu sayfa arşivi JavaScript ile yükler. Ham dosya:": "This page loads the archive with JavaScript. Raw file:",
    // yontem.html (prose is bilingual in the page itself)
    "Makro hava nasıl ölçülüyor?": "How is the macro weather measured?",
    "Makro hava nasıl ölçülüyor? — Piyasa Hava Durumu": "How is the macro weather measured? — Piyasa Hava Durumu",
    "Kural sürümü v1 · dondurulma 21 Kasım 2026": "Rules v1 · frozen on 21 November 2026",
    // hafta.html
    "Haftalık": "Weekly", "Cuma baskısı": "Friday edition", "Pazartesi baskısı": "Monday edition",
    "Dünyada bu hafta": "The world this week", "Dünyada bu hafta — Piyasa Hava Durumu": "The world this week — Piyasa Hava Durumu",
    "Bu hafta şimdiye kadar": "This week so far", "Geçmiş yıllarda bu hafta": "This week in past years",
    "Yıl yıl": "Year by year", "Bu haftanın takvimi": "This week's calendar", "Tarihte bu hafta": "This week in history",
    "İlkler": "Firsts", "Bu sayfa haftalık veriyi JavaScript ile yükler.": "This page loads the weekly data with JavaScript.",
    "Haftalık baskı henüz yayımlanmadı ya da yüklenemedi.": "The weekly edition is not published yet or could not be loaded.",
    "Geçmiş yıllardaki hareketler yalnız tarihsel bilgidir; gelecek hakkında bir şey söylemez. Yatırım tavsiyesi değildir.":
      "Past years' moves are historical information only; they say nothing about the future. Not investment advice.",
    // dunya.html
    "Dünyada durum ne? — Piyasa Hava Durumu": "How is the world doing? — Piyasa Hava Durumu",
    "Bölge bölge endeks ve fonlar: son kapanış, değişim (1 gün, 7 gün, 30 gün, yıl başı = YB) ve 20, 50, 200 günlük ortalamaya göre yer.":
      "Indices and funds region by region: last close, change (1 day, 7 days, 30 days, year to date = YTD) and position versus the 20-, 50- and 200-day average.",
    "altında. Sabit sıra; bir sıralama değildir.": "below. Fixed order; not a ranking.",
    "Seviye": "Level", "1g": "1D", "7g": "7D", "30g": "30D", "YB": "YTD", "20g": "20D", "50g": "50D", "200g": "200D",
    "Yerel para birimiyle değişim. Liste piyasa değeri büyüklüğüne göre bir kez belirlendi; sıralama değildir.":
      "Change in local currency. The list was set once by market value; it is not a ranking.",
    "Emtialar": "Commodities", "Değerli metaller": "Precious metals", "Sanayi metali": "Industrial metal", "Enerji": "Energy", "Tarım": "Agriculture",
    "Vadeli işlem sözleşmelerinin (yakın vade) günlük kapanışı, sözleşmenin kendi biriminde.": "Daily close of the front-month futures contract, in the contract's own unit.",
    "Değerli metaller — referans": "Precious metals — reference",
    "Bu metaller için ücretsiz, günlük ve kamuya açık bir fiyat serisi yok; fiyat gösterilmez.": "There is no free, daily, public price series for these metals; no price is shown.",
    "Rodyum": "Rhodium", "İridyum": "Iridium", "Rutenyum": "Ruthenium", "Osmiyum": "Osmium",
    "— günlük serbest veri yok.": "— no free daily data.",
    "Platin grubu metal; benzinli araç katalitik konvertörlerinde kullanılır. Üretimin büyük kısmı Güney Afrika'dan gelir.":
      "A platinum-group metal used in catalytic converters of petrol cars. Most production comes from South Africa.",
    "Çok yoğun, korozyona dayanıklı platin grubu metal; buji uçları, elektroliz (hidrojen) elektrotları ve kristal büyütme potalarında kullanılır.":
      "A very dense, corrosion-resistant platinum-group metal used in spark-plug tips, electrolysis (hydrogen) electrodes and crystal-growing crucibles.",
    "Platin grubu metal; sabit disk kaplamaları, elektronik dirençler ve kimyasal katalizörlerde kullanılır.":
      "A platinum-group metal used in hard-disk coatings, electronic resistors and chemical catalysts.",
    "Bilinen en yoğun element; çok küçük hacimlerde, özel alaşımlarda kullanılır.": "The densest known element; used in very small amounts in special alloys.",
    "Japonya / Kore teknoloji": "Japan / Korea technology", "Emtia ve madenler": "Commodities and mining", "Büyük şirketler": "Large companies",
    "Yalnız başlık, kaynak, saat ve bağlantı. Haber metni ya da görsel kopyalanmaz; başlıklar kaynağın kendi dilindedir ve sitenin görüşü değildir.":
      "Headline, source, time and link only. No article text or images are copied; headlines are in the source's language and are not the site's opinion.",
    "Kaynaklar ve bekleyen konular": "Sources and pending items",
    "Çin: Şartları başlık listelemeye açıkça izin veren resmî bir akış henüz seçilmedi.": "China: no official feed whose terms clearly allow listing headlines has been chosen yet.",
    "Japonya / Kore teknoloji: Japonya için şartları uygun resmî akış henüz seçilmedi (Kore akışları kullanılıyor).": "Japan / Korea technology: no official feed with suitable terms chosen for Japan yet (Korean feeds are used).",
    "Midas'ın Kulakları: getmidas.com'da resmî RSS/API bulunamadı; site 'Tüm hakları saklıdır' diyor. Boran'ın onayı/izin yazışması olmadan eklenmeyecek.":
      "Midas: no official RSS/API found on getmidas.com and the site says 'All rights reserved'; not added without permission.",
    "Bölgeye ve varlık sınıfına göre sabit sıra, listeler alfabetik; bir performans sıralaması ya da öneri değildir. Şirket listeleri belirlendiği tarihteki yaklaşık piyasa değeri büyüklüğüne göre seçildi ve üç ayda bir gözden geçirilir. Borsalar farklı saat dilimlerinde kapanır; tarih sütunu her satırın kendi kapanış gününü gösterir.":
      "Fixed order by region and asset class, lists alphabetical; not a performance ranking and not advice. Company lists were chosen by approximate market value on the date they were set and are reviewed quarterly. Exchanges close in different time zones; the date column shows each row's own closing day.",
    "Bu sayfa nasıl hazırlanıyor?": "How is this page prepared?",
    "Bu sayfadaki fiyat türevleri yalnızca görüntüleme içindir (": "Price derivatives on this page are for display only (",
    "ayrıntı": "details", "Bu sayfa dünya verisini JavaScript ile yükler.": "This page loads world data with JavaScript."
  }, [
    [/^(\d+)\/(\d+) yıl yükseliş$/, function (m) { return m[1] + "/" + m[2] + " years up"; }],
    [/^(.+): endeks ve fonlar$/, function (m) { return m[1] + ": indices and funds"; }],
    [/^(.+): büyük şirketler$/, function (m) { return m[1] + ": large companies"; }],
    [/^En büyük şirketler \((\d+), alfabetik\)$/, function (m) { return "Largest companies (" + m[1] + ", alphabetical)"; }],
    [/^(.*)Liste (.+) tarihinde belirlendi, üç ayda bir \(sonraki gözden geçirme: (.+)\)$/, function (m) {
      return m[1] + "List set on " + m[2] + ", reviewed quarterly (next review: " + m[3] + ")"; }]
  ], [
    ["Altın (USD/ons)", "Gold (USD/oz)"], ["Gümüş (USD/ons)", "Silver (USD/oz)"], ["Paladyum (USD/ons)", "Palladium (USD/oz)"],
    ["Platin (USD/ons)", "Platinum (USD/oz)"], ["Bakır (USD/libre)", "Copper (USD/lb)"], ["Doğal gaz (Henry Hub)", "Natural gas (Henry Hub)"],
    ["Buğday (ABD senti/buşel)", "Wheat (US cents/bushel)"], ["Mısır (ABD senti/buşel)", "Corn (US cents/bushel)"],
    ["Soya fasulyesi (ABD senti/buşel)", "Soybeans (US cents/bushel)"], ["(USD/varil)", "(USD/barrel)"],
    ["ABD Enerji Enformasyon İdaresi (EIA)", "US Energy Information Administration (EIA)"],
    ["Korea.net (Kore Kültür ve Enformasyon Servisi)", "Korea.net (Korean Culture and Information Service)"],
    ["gov.br (Brezilya Hükümeti)", "gov.br (Government of Brazil)"], [" (hata: ", " (error: "],
    [" · Liste ", " · List set on "], [" tarihinde belirlendi, üç ayda bir (sonraki gözden geçirme: ", ", reviewed quarterly (next review: "],
    ["Japonya / Kore teknoloji — ", "Japan / Korea technology — "], ["Emtia ve madenler — ", "Commodities and mining — "],
    ["Büyük şirketler — ", "Large companies — "], ["Brezilya — ", "Brazil — "],
    ["Japonya", "Japan"], ["Güney Kore", "South Korea"], ["Çin", "China"], ["Tayvan", "Taiwan"], ["Brezilya", "Brazil"],
    ["Şubat ", "February "], ["Mayıs ", "May "], ["Ağustos ", "August "], ["Kasım ", "November "]
  ]);
})();
