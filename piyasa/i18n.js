/* Piyasa Hava Durumu — language switch (S13). Türkçe is the default; English is chosen with
   ?lang=en (no cookies, no storage: the choice travels in the link). In English mode every text
   node the page shows (static HTML and anything scripts write later) is translated through
   an exact-match dictionary, a few sentence patterns and Turkish→English number/date format.
   Only textContent / nodeValue / attributes are touched; nothing is parsed as HTML.
   Data sentences that come from the daily build use their *_en fields (see app.js). */
(function () {
  "use strict";
  var q = /[?&]lang=(en|tr)\b/.exec(location.search);
  var LANG = q ? q[1] : "tr";
  var EN = LANG === "en";
  document.documentElement.lang = LANG;

  var MON_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var MON_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  var D = {
    // masthead, nav, footer
    "İstatistik yalan söylemez": "Statistics don't lie",
    "Seviye, dokuz piyasa göstergesinden kaçının stres işareti verdiğini özetler; ne yapılacağını söylemez ve KIRMIZI günlerinin hepsini bir düşüş izlemedi (":
      "The level summarises how many of nine market indicators show stress; it does not say what to do, and not every RED day was followed by a fall (",
    "Sicil": "Track record",
    "). Makro veriler ABD kaynaklıdır ve bir iş günü gecikmeli gelir.": "). Macro inputs come from US sources and arrive one business day late.",
    "Site": "Site", "Ayarlar": "Settings", "Sayfanı düzenle": "Edit your page",
    "Bölümlerin ve haber konularının sırasını sen seç; ayarın yalnız bu cihazda kalır.": "Choose the order of sections and news topics; the setting stays on this device only.",
    "Hesapla": "Calculator", "Arşiv": "Archive", "Yöntem": "Method", "Bugün": "Today",
    "Yatırım tavsiyesi değildir. Veriler bilgi amaçlıdır.": "Not investment advice. Data for information only.",
    "© Piyasa Hava Durumu — türetilmiş veriler kaynak gösterilerek kullanılabilir (CC BY 4.0)":
      "© Piyasa Hava Durumu (Market Weather) — derived data may be reused with attribution (CC BY 4.0)",
    "Veri uçları (JSON/CSV)": "Data endpoints (JSON/CSV)",
    "Daha derin araçlar": "Deeper tools",
    "Öneri ve hata bildir": "Suggestions & bug reports",
    "Yükleniyor…": "Loading…", "Veri yükleniyor…": "Loading data…", "—": "—",
    // home
    "Piyasa bandı: 1 günlük değişim": "Market band: 1-day change",
    "Makro hava": "Macro weather", "Tarih seç": "Pick a date", "Bugüne dön": "Back to today",
    "Geçmiş bir günün kaydı, o gün yayımlandığı gibi.": "A past day's record, exactly as published that day.",
    "Bu sayfa günlük veriyi JavaScript ile yükler. Kuralların açıklaması için": "This page loads daily data with JavaScript. For the rules, see the",
    "sayfasına bakabilirsiniz.": "page.",
    "Kurallar": "Rules",
    "Her satır bir kural. Kırmızı nokta: kural bugün olumsuz işaret veriyor (1 puan). Boş daire: vermiyor. Başlığa dokununca kuralın ne ölçtüğü açılır.":
      "One rule per line. Red dot: the rule gives a negative signal today (1 point). Empty circle: it doesn't. Tap a title to see what the rule measures.",
    "Ayrıntı": "Detail", "TL tarafı": "The lira side", "TL verisi yükleniyor…": "Loading lira data…",
    "Benim pozisyonum ne durumda?": "How is my position doing?",
    "Bu hafta": "This week",
    "Dünyada bu hafta: geçmiş yıllarda bu hafta ne oldu?": "This week in the world: what happened in this week in past years?",
    "Her pazartesi ve cuma: aynı haftanın son 10 yıldaki seyri, haftanın veri takvimi ve ekonomi tarihinden notlar.":
      "Every Monday and Friday: the same week over the last 10 years, the week's data calendar and notes from economic history (in Turkish).",
    "Ortalamalar": "Moving averages",
    "Fiyatlar ortalamalarına göre nerede?": "Where are prices versus their averages?",
    "BIST 100, gram altın, dolar/TL, ABD fonları, Bitcoin, Ethereum ve büyük şirketler: 20, 50 ve 200 günlük ortalamaya göre konum.":
      "BIST 100, gold per gram, USD/TRY, US funds, Bitcoin, Ethereum and large companies: position versus the 20-, 50- and 200-day average.",
    "Günün hareketlileri": "Today's movers",
    "Bugün piyasada neler oldu?": "What happened in the markets today?",
    "Borsa İstanbul, ABD ve kriptoda en çok yükselen ve düşen isimler, olağandışı hacim ve hareketler.":
      "Biggest gainers and losers on Borsa Istanbul, in the US and in crypto, with unusual volume and moves.",
    "Dünya": "World", "Dünyada durum ne?": "How is the world doing?",
    "Japonya, Kore, Çin, Hong Kong, Tayvan, Brezilya, emtialar ve günün başlıkları. Sayfa yalnız açılınca yüklenir.":
      "Japan, Korea, China, Hong Kong, Taiwan, Brazil, commodities and the day's headlines. Loaded only when opened.",
    "Senin pozisyonun": "Your position", "Sor": "Ask", "Sorular": "Questions", "Kolay ekonomi": "Plain economics (Turkish)", "Kur, altın, enflasyon ve faiz; sade dille ve örneklerle.": "Exchange rate, gold, inflation and interest rates, explained simply.", "Daha fazlası": "More",
    "Dünyada bu hafta": "This week in the world",
    "Benim pozisyonum ne durumda? Maliyetini gir, başa baş fiyatını gör": "How is my position doing? Enter your cost, see your breakeven price",
    "Borsa İstanbul, ABD ve kriptoda günün hareketlileri.": "Today's movers on Borsa Istanbul, in the US and in crypto.",
    "Asya, Brezilya, emtialar ve günün başlıkları.": "Asia, Brazil, commodities and today's headlines.",
    "Geçmiş yıllarda bu hafta ne oldu (pazartesi ve cuma).": "What happened this week in past years (Mondays and Fridays).",
    "20, 50 ve 200 günlük ortalamaya göre konum.": "Position versus the 20-, 50- and 200-day averages.",
    "2–3 varlık aynı grafikte ya da oran olarak.": "2–3 assets on one chart, or as a ratio.",
    "Cevaplar her sabah verilerle birlikte hazırlanır; sayılar doğrudan veriden gelir.":
      "Answers are prepared every morning with the data; every number comes straight from the data.",
    "Dünya özeti": "World summary",
    "Veri şu an yüklenemedi": "Data could not be loaded right now",
    "Günlük veri dosyasına ulaşılamadı. Biraz sonra yeniden deneyin.": "The daily data file could not be reached. Please try again shortly.",
    "Makro hava verisi yok": "No macro weather data",
    "Başlıklara göre": "By group",
    "Ham skor. 0–2 YEŞİL, 3–4 SARI, 5 ve üzeri KIRMIZI; seviye ikinci gün onayıyla değişir.":
      "Raw score. 0–2 GREEN, 3–4 YELLOW, 5 or more RED; the level changes only after a second-day confirmation.",
    "Likidite": "Liquidity", "Dolar": "Dollar", "Kredi / risk": "Credit / risk", "Nakde kaçış": "Dash for cash", "Petrol": "Oil",
    "Nedir?": "What is it?", "Neden izleniyor?": "Why watch it?", "Nasıl hesaplanıyor?": "How is it calculated?", "Kaynak:": "Source:",
    "Nedir? ": "What is it? ", "Nasıl hesaplanıyor? ": "How is it calculated? ", "Kaynak: ": "Source: ", "Değişimler: ": "Changes: ",
    "Yöntem sayfasında oku": "Read on the Method page", "Yöntem sayfası": "Method page",
    "Bu kural için açıklama yok.": "No explanation for this rule.",
    // rule explanations (app.js EXPLAIN)
    "Dolara sabitlenmiş kripto paraların (USDT, USDC…) toplam piyasa değeri.": "Total market value of dollar-pegged crypto coins (USDT, USDC…).",
    "Kripto piyasasına giren ya da çıkan nakdin kaba bir ölçüsüdür. Arz küçülüyorsa piyasadan nakit çekiliyor demektir.":
      "A rough measure of cash entering or leaving crypto. A shrinking supply means cash is being withdrawn.",
    "Son 7 günde toplam arz azaldıysa işaret verir.": "Signals if total supply fell over the last 7 days.",
    "Fed bilançosundan Hazine'nin Fed'deki hesabı ve ters repo çıkarıldığında kalan tutar.": "The Fed balance sheet minus the Treasury's account at the Fed and reverse repo.",
    "Piyasadaki dolar bolluğunun yaygın bir göstergesidir; azalması likiditenin daraldığına işaret eder.": "A common gauge of dollar abundance; a decline points to tighter liquidity.",
    "20 gün öncesine göre azaldıysa işaret verir. Haftalık yayımlanır.": "Signals if it is lower than 20 days ago. Published weekly.",
    "ABD'nin 10 yıllık enflasyona endeksli tahvil faizi: enflasyondan arındırılmış borçlanma maliyeti.": "The US 10-year inflation-indexed bond yield: the cost of borrowing net of inflation.",
    "Reel faiz yükselince parayı riskli varlıkta tutmanın maliyeti artar.": "When real yields rise, holding money in risky assets costs more.",
    "20 günde en az 0,15 puan (15 baz puan) yükseldiyse işaret verir.": "Signals if it rose at least 0.15 points (15 basis points) over 20 days.",
    "Doların başlıca para birimlerine karşı değerini ölçen endeks.": "An index of the dollar against major currencies.",
    "Hızlı dolar güçlenmesi dünya genelinde finansmanı zorlaştırır.": "A fast-rising dollar tightens financing worldwide.",
    "20 günde en az %1 yükseldiyse işaret verir. Endeks lisanslı olduğu için yalnız yön gösterilir.": "Signals if it rose at least 1% over 20 days. The index is licensed, so only its direction is shown.",
    "ABD'de düşük kredi notlu şirket tahvillerinin devlet tahviline göre ödediği ek faiz.": "The extra yield low-rated US corporate bonds pay over government bonds.",
    "Bu fark açılıyorsa piyasa şirketlerin borcunu daha riskli görüyor demektir.": "A widening spread means the market sees corporate debt as riskier.",
    "20 günde en az 0,25 puan açıldıysa işaret verir. Lisanslı seri: yalnız işaret ve yön.": "Signals if it widened at least 0.25 points over 20 days. Licensed series: signal and direction only.",
    "Yükselmesi piyasada belirsizliğin ve korumaya talebin arttığını gösterir.": "A rise shows more uncertainty and more demand for protection.",
    "18 veya üzerindeyse işaret verir.": "Signals at 18 or above.",
    "ABD teknoloji ağırlıklı Nasdaq Bileşik endeksi.": "The tech-heavy US Nasdaq Composite index.",
    "Risk iştahının en hızlı tepki veren göstergelerinden biridir.": "One of the fastest-reacting gauges of risk appetite.",
    "20 günde en az %3 düştüyse işaret verir. Lisanslı endeks: yalnız işaret ve yön.": "Signals if it fell at least 3% over 20 days. Licensed index: signal and direction only.",
    "Altın ile doların aynı anda nasıl hareket ettiği.": "How gold and the dollar move together.",
    "Normalde güvenli liman olan altın düşerken dolar yükseliyorsa, yatırımcılar her şeyi satıp nakde geçiyor olabilir.":
      "If gold, normally a safe haven, falls while the dollar rises, investors may be moving everything into cash.",
    "Altın 20 günde en az %3 düştüyse ve aynı dönemde dolar endeksi yükseldiyse işaret verir.": "Signals if gold fell at least 3% over 20 days while the dollar index rose.",
    "WTI ham petrol vadeli fiyatı.": "WTI crude oil futures price.",
    "Sert yükseliş enflasyon baskısına, kredi primi açılırken sert düşüş talep zayıflığına işaret edebilir. Bunlar olası yorumlardır: petrol arz artışı ya da jeopolitik primin sönmesiyle de düşebilir.":
      "A sharp rise may point to inflation pressure; a sharp fall while credit spreads widen may point to weak demand. These are possible readings: oil can also fall on more supply or a fading geopolitical premium.",
    "20 günde en az %10 yükseldiyse ya da en az %15 düşüp kredi primi açılıyorsa işaret verir.": "Signals if it rose at least 10% over 20 days, or fell at least 15% while the credit spread widens.",
    "FRED (Federal Reserve)": "FRED (Federal Reserve)", "Yahoo Finance (ICE DXY)": "Yahoo Finance (ICE DXY)",
    "Yahoo Finance (altın vadeli, DXY)": "Yahoo Finance (gold futures, DXY)", "Yahoo Finance (WTI vadeli)": "Yahoo Finance (WTI futures)",
    // TL side + band
    "Gram altın": "Gold (gram)", "Gram gümüş": "Silver (gram)", "Dolar/TL": "USD/TRY", "Ons altın": "Gold (ounce)", "Ons gümüş": "Silver (ounce)",
    "Brent petrol": "Brent oil", "WTI petrol": "WTI oil", "BIST 100 ($)": "BIST 100 ($)", "Bitcoin": "Bitcoin", "Ether": "Ether",
    "BIST 100 (dolar bazında)": "BIST 100 (in dollars)", "Bitcoin (dolar)": "Bitcoin (USD)", "Ether (dolar)": "Ether (USD)",
    "1 gün": "1 day", "7 gün": "7 days", "30 gün": "30 days", "Yılbaşı": "YTD", "1 yıl": "1 year", "200g ort. farkı": "vs 200-day avg",
    "1 günlük değişim": "1-day change", "Veri yok.": "No data.", "Veri yok": "No data", "veri yok": "no data",
    "TL verisi bugün güncellenmedi; son geçerli değerler gösteriliyor.": "Lira data was not updated today; last valid values shown.",
    "TL verisi henüz yayımlanmadı.": "Lira data not published yet.",
    "1 gram altının TL karşılığı.": "The lira price of one gram of gold.",
    "1 gram gümüşün TL karşılığı.": "The lira price of one gram of silver.",
    "1 ABD dolarının TL karşılığı (piyasa kuru).": "The lira price of one US dollar (market rate).",
    "BIST 100 endeksinin dolar cinsinden değeri.": "The BIST 100 index in US dollars.",
    "Bitcoin'in dolar fiyatı (günlük kapanış, UTC).": "Bitcoin's dollar price (daily close, UTC).",
    "Ether'in dolar fiyatı (günlük kapanış, UTC).": "Ether's dollar price (daily close, UTC).",
    "Ons altın fiyatı (dolar) × dolar/TL ÷ 31,1035 (1 ons = 31,1035 gram). Kuyumcu satış fiyatı değildir; işçilik ve makas içermez.":
      "Gold price per ounce (USD) × USD/TRY ÷ 31.1035 (1 ounce = 31.1035 grams). Not a jeweller's price; no workmanship or spread.",
    "Ons gümüş fiyatı (dolar) × dolar/TL ÷ 31,1035. Banka ve kuyumcu fiyatları makas nedeniyle farklı olabilir.":
      "Silver price per ounce (USD) × USD/TRY ÷ 31.1035. Bank and jeweller prices differ because of spreads.",
    "Günlük kapanış kuru. Banka ve döviz bürosu kurları alış-satış makası nedeniyle farklıdır.": "Daily closing rate. Bank and exchange-office rates differ because of the bid-ask spread.",
    "BIST 100 ÷ dolar/TL. Grafikte başlangıç günü 100 kabul edilir; böylece TL'deki değer kaybından arındırılmış performans görülür.":
      "BIST 100 ÷ USD/TRY. The chart starts at 100, showing performance net of the lira's depreciation.",
    "Kripto piyasası 7/24 açıktır; günlük kapanış UTC gece yarısı alınır.": "Crypto trades 24/7; the daily close is taken at UTC midnight.",
    "Kripto piyasası 7/24 açıktır; günlük kapanış UTC gece yarısı alınır. Hesaplayıcı OKX kapanışını kullanır, küçük fark olabilir.":
      "Crypto trades 24/7; the daily close is taken at UTC midnight. The calculator uses the OKX close, so small differences are possible.",
    "1 gün: bir önceki kapanışa göre. 7 ve 30 gün: o kadar takvim günü önceki son kapanışa göre. Yılbaşı: geçen yılın son kapanışına göre. 1 yıl: 365 gün önceki son kapanışa göre. 200g ort. farkı: son 200 işlem gününün ortalamasına göre uzaklık. Grafikte siyah çizgi kapanış, kırmızı çizgi 200 günlük ortalama.":
      "1 day: vs the previous close. 7 and 30 days: vs the last close that many calendar days ago. YTD: vs last year's final close. 1 year: vs the last close 365 days ago. vs 200-day avg: distance from the average of the last 200 trading days. On the chart the black line is the close, the red line the 200-day average.",
    "Endeks seviyesi yerine dolar bazında değişim gösterilir.": "Shown as change in dollar terms instead of the index level.",
    // konum
    "Konum tablosu": "Position table", "Ortalamalara göre konum": "Position versus moving averages",
    "Bu sayfa günlük veriyi JavaScript ile yükler. Tablonun nasıl hesaplandığı": "This page loads daily data with JavaScript. How the table is calculated:",
    "sayfasında.": "page.",
    "Her satırda son kapanışın 20, 50 ve 200 günlük basit ortalamaya göre yeri.": "Each row shows the last close versus its 20-, 50- and 200-day simple average.",
    "üstünde,": "above,",
    "altında. Fark: son kapanışın 200 günlük ortalamaya yüzde uzaklığı. Varlık sınıfına göre gruplu, grup içinde alfabetik; bir sıralama değildir.":
      "below. Gap: the last close's % distance from the 200-day average. Grouped by asset class, alphabetical within a group; not a ranking.",
    "Bu tablo nasıl hesaplanıyor?": "How is this table calculated?",
    "Varlık": "Asset", "Fark": "Gap", "Veri": "Data",
    "Türkiye": "Türkiye", "ABD endeks fonları": "US index funds", "Emtia fonları": "Commodity funds", "Kripto": "Crypto", "ABD büyük şirketler": "Large US companies",
    "BIST 100 (TL)": "BIST 100 (TRY)", "Gram altın (TL)": "Gold per gram (TRY)", "Gram gümüş (TL)": "Silver per gram (TRY)",
    "QQQ (Nasdaq 100 fonu)": "QQQ (Nasdaq 100 fund)", "RSP (S&P 500 eşit ağırlık fonu)": "RSP (S&P 500 equal-weight fund)",
    "SMH (yarı iletken fonu)": "SMH (semiconductor fund)", "SPY (S&P 500 fonu)": "SPY (S&P 500 fund)",
    "GLD (altın fonu)": "GLD (gold fund)", "SLV (gümüş fonu)": "SLV (silver fund)",
    "yeterli geçmiş yok": "not enough history", "Konum tablosu henüz yayımlanmadı ya da yüklenemedi.": "The position table is not published yet or could not be loaded.",
    "Olgusal konum tablosu: varlık sınıfına göre gruplu, grup içinde alfabetik. Sıralama ya da öneri değildir. Fiyat seviyesi yayımlanmaz. Girdi kaynağı Yahoo Finance ve OKX (kişisel kullanım şartlı); ticari kullanım öncesi lisanslı kaynakla değiştirilecek.":
      "A factual position table: grouped by asset class, alphabetical within a group. Not a ranking or a recommendation. Price levels are not published. Inputs: Yahoo Finance and OKX (personal-use terms); to be replaced by a licensed source before any commercial use.",
    // hareket
    "Piyasa özeti": "Market summary",
    "Bu sayfa günlük veriyi JavaScript ile yükler. Kurallar": "This page loads daily data with JavaScript. The rules are on the",
    "Bir önceki işlem gününün kapanışına göre 1 günlük yüzde değişim. Göreli hacim: o günün hacmi ÷ önceki 20 günün ortalaması. Yalnız likit isimler; fiyat seviyesi gösterilmez. Olağandışı hareketler alfabetik dizilir.":
      "1-day % change versus the previous trading day's close. Relative volume: the day's volume ÷ the average of the previous 20 days. Liquid names only; price levels are not shown. Unusual moves are listed alphabetically.",
    "Listeler ve kurallar nasıl hesaplanıyor?": "How are the lists and rules calculated?",
    "Borsa İstanbul": "Borsa Istanbul", "ABD": "United States",
    "En çok yükselenler": "Biggest gainers", "En çok düşenler": "Biggest losers", "Sembol": "Symbol", "Değişim": "Change", "Göreli hacim": "Relative volume",
    "Bugün bu yönde isim yok.": "No names in this direction today.", "Bugün kurallara takılan hareket yok.": "No moves matched the rules today.",
    "Bu pazar için henüz veri yok.": "No data for this market yet.", "Bu pazarın verisi güncel değil; liste gösterilmiyor.": "This market's data is not current; list hidden.",
    "Neden? ": "Why? ",
    "Neden? Haber eşleştirmesi bekleniyor. Hareketlerin nedeni tahmin edilmez; kaynaklı başlık eşleşince burada gösterilecek.":
      "Why? Waiting for news matching. Causes are never guessed; a sourced headline will appear here once matched.",
    "Neden? satırları yalnız kaynaklı haber başlıklarıdır; hareketin nedeni hakkında yorum değildir.": "Why? lines are sourced headlines only, not commentary on the cause.",
    "Günün hareketlileri henüz yayımlanmadı ya da yüklenemedi.": "Today's movers are not published yet or could not be loaded.",
    "52 haftanın en yükseği": "52-week high", "52 haftanın en düşüğü": "52-week low",
    "BIST verisi gecikmeli olabilir; kapanış sonrası değerler kullanılır.": "BIST data may be delayed; post-close values are used.",
    "Evren: araştırma listesindeki ABD hisseleri (fonlar hariç).": "Universe: US stocks on the research list (funds excluded).",
    // dünya side
    "Dünya · son gün": "World · last day", "Günün başlıkları": "Today's headlines",
    "Japonya": "Japan", "Güney Kore": "South Korea", "Çin": "China", "Tayvan": "Taiwan", "Brezilya": "Brazil", "Hong Kong": "Hong Kong",
    "Şanghay Bileşik": "Shanghai Composite",
    "Stablecoin arzı": "Stablecoin supply", "Fed net likiditesi": "Fed net liquidity", "Reel faiz": "Real yield",
    "Dolar endeksi": "Dollar index", "Kredi risk primi": "Credit spread", "Oynaklık (VIX)": "Volatility (VIX)",
    "Nasdaq Bileşik": "Nasdaq Composite", "Altın ve dolar": "Gold and dollar",
    "Değişimler:": "Changes:",
    "S&P 500 opsiyonlarından hesaplanan beklenen oynaklık; \"korku endeksi\" olarak da bilinir.": "Expected volatility implied by S&P 500 options; also known as the \"fear index\".",
    "Yahoo Finance: COMEX altın vadeli (GC=F) ve USD/TRY": "Yahoo Finance: COMEX gold futures (GC=F) and USD/TRY",
    "Yahoo Finance: COMEX gümüş vadeli (SI=F) ve USD/TRY": "Yahoo Finance: COMEX silver futures (SI=F) and USD/TRY",
    "Yahoo Finance: XU100.IS (gecikmeli olabilir) ve USD/TRY": "Yahoo Finance: XU100.IS (may be delayed) and USD/TRY",
    "Hesaplama: gram altın TL = ons altın (USD) × USD/TRY ÷ 31,1035; gram gümüş aynı şekilde. Girdi kaynağı Yahoo Finance (kişisel kullanım şartlı); ticari kullanım öncesi lisanslı kaynakla değiştirilecek.":
      "Calculation: gold per gram in TRY = gold per ounce (USD) × USD/TRY ÷ 31.1035; silver the same way. Input source: Yahoo Finance (personal-use terms); to be replaced by a licensed source before any commercial use.",
    "Makro hava geçmişi (ham skor, 0–9)": "Macro weather history (raw score, 0–9)",
    "Günlük ham skor; gri geriye dönük, siyah canlı, kırmızı canlı KIRMIZI gün": "Daily raw score; grey retro, black live, red live RED days",
    "Geriye dönük": "Retro", "Canlı": "Live", "Canlı, KIRMIZI": "Live, RED", "canlı": "live",
    "Kapanış": "Close", "50 gün ort.": "50-day avg", "200 gün ort.": "200-day avg",
    "Grafik kütüphanesi:": "Chart library:", "Grafik şu an yüklenemedi.": "The chart could not be loaded right now.",
    "OKX USDT vadeli günlük mumları (UTC günü). Kripto 7/24 işlem gördüğü için açılış boşluğu nadirdir. Mum hacmi kontrat cinsinden olduğundan işlem hacmi tabanı uygulanmaz; evren zaten en büyük ~30 coinden oluşur.":
      "OKX USDT perpetual daily candles (UTC day). Crypto trades 24/7, so opening gaps are rare. Candle volume is in contracts, so no turnover floor is applied; the universe is already the ~30 largest coins.",
    // karşılaştır
    "Grafik": "Chart", "Grafikte karşılaştır": "Compare on a chart",
    "Altın, gümüş, dolar/TL, petrol, BIST 100, Bitcoin ve ABD fonlarından 2–3 tanesini aynı grafikte gör ya da birbirine oranla (ör. altın/gümüş oranı).":
      "See 2–3 of gold, silver, USD/TRY, oil, BIST 100, Bitcoin and US funds on one chart, or as a ratio (e.g. the gold/silver ratio).",
    "Bu sayfa grafik için JavaScript kullanır.": "This page uses JavaScript for the chart.",
    "1. varlık": "Asset 1", "2. varlık": "Asset 2", "3. varlık (isteğe bağlı)": "Asset 3 (optional)",
    "Görünüm": "View", "Birlikte (başlangıç = 100)": "Together (start = 100)", "Oran (1. ÷ 2.)": "Ratio (1 ÷ 2)",
    "Aralık": "Range", "1 ay": "1M", "3 ay": "3M", "6 ay": "6M", "2 yıl": "2Y", "Hazır:": "Presets:",
    "Altın / gümüş oranı": "Gold / silver ratio", "Gram altın ve dolar/TL": "Gold per gram and USD/TRY",
    "BIST 100: TL ve dolar": "BIST 100: lira and dollar", "Altın, Bitcoin, S&P 500": "Gold, Bitcoin, S&P 500",
    "Brent / altın oranı": "Brent / gold ratio", "Karşılaştırma grafiği": "Comparison chart",
    "Sürükle: kaydır · tekerlek ya da iki parmak: yakınlaştır · çift tıkla: sığdır. \"Birlikte\" görünümünde her seri aralığın ilk günü 100 kabul edilerek çizilir; böylece farklı birimlerdeki varlıkların yüzde hareketi yan yana görülür. BIST 100 ve fonlar yalnız endekslenmiş seri olarak yayımlanır.":
      "Drag: pan · wheel or two fingers: zoom · double-click: fit. In the \"Together\" view each series starts at 100 on the first day of the range, so % moves of assets in different units sit side by side. BIST 100 and funds are published as rebased series only.",
    "Oran için iki farklı varlık seç.": "Pick two different assets for a ratio.", "En az bir varlık seç.": "Pick at least one asset.",
    "Bu iki varlığın ortak günü yok.": "These two assets have no common days.",
    "Karşılaştırma verisi henüz yayımlanmadı ya da yüklenemedi.": "Comparison data is not published yet or could not be loaded.",
    "Günlük kapanışlar, son ~2 yıl. BIST 100 ve fonlar yalnız 100'e endeksli seri olarak yayımlanır (seviye değil). Girdi kaynağı Yahoo Finance (kişisel kullanım şartlı).":
      "Daily closes, last ~2 years. BIST 100 and funds are published only as series rebased to 100 (not levels). Input source: Yahoo Finance (personal-use terms).",
    "Grafik kütüphanesi: ": "Chart library: ",
    // günün özeti
    "Günün özeti": "Today's digest", "Merkez bankaları": "Central banks", "Dünya ekonomisi": "World economy",
    "Altın ve emtia": "Gold and commodities", "Şirketler": "Companies", "Asya": "Asia", "Latin Amerika": "Latin America",
    // other pages: a notice is shown instead of a full translation
    "Hesaplayıcı": "Calculator"
  };

  function enNum(s) { return s.replace(/\./g, "\u0001").replace(/,/g, ".").replace(/\u0001/g, ","); }
  var MON_RE = new RegExp("(\\d{1,2}) (" + MON_TR.join("|") + "|" + MON_TR.map(function (m) { return m.slice(0, 3); }).join("|") + ")(?![a-zçğıöşü])", "g");
  var P = [
    [/^(.*) — Makro hava: (YEŞİL|SARI|KIRMIZI)$/, function (m) { return m[1] + " — Macro weather: " + LVL[m[2]]; }],
    [/^Makro hava: (YEŞİL|SARI|KIRMIZI) — Piyasa Hava Durumu$/, function (m) { return "Macro weather: " + LVL[m[1]] + " — Piyasa Hava Durumu"; }],
    [/^Veri: (.+) kapanışı · Kural sürümü (\S+) · Kayıt: (canlı|geriye dönük|—)$/, function (m) {
      return "Data: " + m[1] + " close · Rules " + m[2] + " · Record: " + ({ "canlı": "live", "geriye dönük": "retro", "—": "—" })[m[3]]; }],
    [/^Veri tarihi (.+) · Kural sürümü (\S+) · Üretildi (.+)$/, function (m) { return "Data date " + m[1] + " · Rules " + m[2] + " · Generated " + m[3]; }],
    [/^Veri tarihi (.+) · Üretildi (.+)$/, function (m) { return "Data date " + m[1] + " · Generated " + m[2]; }],
    [/^Karşılaştırma tarihi: (.+) \(20 gün önce\)\.$/, function (m) { return "Comparison date: " + m[1] + " (20 days earlier)."; }],
    [/^Verinin tarihi: (.+?)( · Karşılaştırma: (.+))?$/, function (m) { return "Data date: " + m[1] + (m[3] ? " · Comparison: " + m[3] : ""); }],
    [/^Güncellenmedi\. Gösterilen son iyi veri: (.+)\. Yeni veri gelene kadar seviye değişmez\.$/, function (m) {
      return "Not updated. Showing the last good data: " + m[1] + ". The level won't change until new data arrives."; }],
    [/^Arşiv kaydı: (.+?)\. O gün yayımlandığı gibi gösteriliyor; yeniden hesaplanmadı\.(.*)$/, function (m) {
      return "Archive record: " + m[1] + ". Shown as published that day; not recomputed." +
        m[2].replace(" Bu kayıtta belgelenmiş bir düzeltme var (Yöntem sayfası).", " This record has a documented correction (Method page).")
            .replace(" TL tarafı bugünün verisini gösterir.", " The lira side shows today's data."); }],
    [/^(.+) için kayıt bulunamadı\. Arşiv sayfasında kayıtlı günler listelenir\.$/, function (m) { return "No record for " + m[1] + ". The Archive page lists recorded days."; }],
    [/^(İşaret var|İşaret yok|Veri yok): (.+)$/, function (m) { return ({ "İşaret var": "Signal", "İşaret yok": "No signal", "Veri yok": "No data" })[m[1]] + ": " + (D[m[2]] || m[2]); }],
    [/^1 günlük değişim · (.+?) itibarıyla \(~15 dk gecikmeli\)( · Altın, gümüş ve petrole dokununca görünüm değişir)?$/, function (m) {
      return "1-day change · as of " + m[1] + " (~15 min delayed)" + (m[2] ? " · Tap gold, silver or oil to switch the view" : ""); }],
    [/^1 günlük değişim · (.+?) verisi( · Altın, gümüş ve petrole dokununca görünüm değişir)?$/, function (m) {
      return "1-day change · data of " + m[1] + (m[2] ? " · Tap gold, silver or oil to switch the view" : ""); }],
    [/^1 günlük değişim · (.+?) kapanışı( · Altın, gümüş ve petrole dokununca görünüm değişir)?$/, function (m) {
      return "1-day change · " + m[1] + " close" + (m[2] ? " · Tap gold, silver or oil to switch the view" : ""); }],
    [/^(.+)\. Dokun: (.+)$/, function (m) {
      var lbl = Object.keys(D).filter(function (k) { return m[1].indexOf(k + " ") === 0; }).sort(function (a, b) { return b.length - a.length; })[0];
      return (lbl ? D[lbl] + m[1].slice(lbl.length) : m[1]) + ". Tap: " + (D[m[2]] || m[2]); }],
    [/^Dokun: (.+)$/, function (m) { return "Tap: " + (D[m[1]] || m[1]); }],
    [/^Veri: (.+?)( · (.+))?$/, function (m) { return "Data: " + m[1] + (m[3] ? " · " + (D[m[3]] || m[3]) : ""); }],
    [/^1 yıl önce \((.+)\): (.+) · bugün: (.+) · değişim (.+)$/, function (m) { return "1 year ago (" + m[1] + "): " + m[2] + " · today: " + m[3] + " · change " + m[4]; }],
    [/^1 yıl önceye \((.+)\) göre değişim: (.+)$/, function (m) { return "Change vs 1 year ago (" + m[1] + "): " + m[2]; }],
    [/^(.+) yılbaşından$/, function (m) { return m[1] + " YTD"; }],
    [/^Son kapanış: (.+?)( · Evren (.+) tarihinde belirlendi)?$/, function (m) { return "Last close: " + m[1] + (m[3] ? " · Universe set on " + m[3] : ""); }],
    [/^(.+?): (\d+) varlığın (\d+) tanesi 200 günlük ortalamasının üstünde\.$/, function (m) { return (D[m[1]] || m[1]) + ": " + m[3] + " of " + m[2] + " assets are above their 200-day average."; }],
    [/^(\d+) varlığın (\d+) tanesi 200 günlük ortalamasının üstünde\.$/, function (m) { return m[2] + " of " + m[1] + " assets are above their 200-day average."; }],
    [/^(.+): ortalamalara göre konum$/, function (m) { return (D[m[1]] || m[1]) + ": position versus moving averages"; }],
    [/^(20|50|200) günlük ortalamanın (üstünde|altında)$/, function (m) { return (m[2] === "üstünde" ? "above" : "below") + " the " + m[1] + "-day average"; }],
    [/^(.+) · eski$/, function (m) { return m[1] + " · stale"; }],
    [/^Üretildi (.+?)( · Evren (.+) tarihinde belirlendi)?$/, function (m) { return "Generated " + m[1] + (m[3] ? " · Universe set on " + m[3] : ""); }],
    [/^(.+) kapanışı · (.+?) (\S+)( · (\d+) likit isim)?$/, function (m) {
      return m[1] + " close · " + (D[m[2]] || m[2].replace("S&P 500 fonu", "S&P 500 fund")) + " " + m[3] + (m[5] ? " · " + m[5] + " liquid names" : ""); }],
    [/^Olağandışı hareketler \((\d+)\)$/, function (m) { return "Unusual moves (" + m[1] + ")"; }],
    [/^Hacim 20 günlük ortalamanın (.+) katı$/, function (m) { return "Volume " + m[1] + "× its 20-day average"; }],
    [/^Açılış boşluğu (.+) \(önceki kapanışa göre\)$/, function (m) { return "Opening gap " + m[1] + " (vs the previous close)"; }],
    [/^Günlük hareket ATR\((\d+)\)'nin (.+) katı$/, function (m) { return "Daily move " + m[2] + "× ATR(" + m[1] + ")"; }],
    [/^Endeks (.+) iken (.+) \(ters yön, (.+) puan fark\)$/, function (m) { return "Index " + m[1] + ", this name " + m[2] + " (opposite direction, " + m[3] + " pt gap)"; }],
    [/^(Japonya|Güney Kore|Çin|Hong Kong|Tayvan|Brezilya) · (.+)$/, function (m) { return D[m[1]] + " · " + (D[m[2]] || m[2]); }],
    [/^Kural sürümü (\S+)$/, function (m) { return "Rules " + m[1]; }],
    [/^(.+) günlük kapanış, 50 ve 200 günlük ortalama$/, function (m) { return m[1] + " daily close, 50- and 200-day average"; }],
    [/^(.+) günlük kapanış \(USDT\)$/, function (m) { return m[1] + " daily close (USDT)"; }],
    [/^(.+): son 1 yıl, siyah çizgi kapanış, kırmızı çizgi 200 günlük ortalama$/, function (m) { return (D[m[1]] || m[1]) + ": last year, black line close, red line 200-day average"; }]
  ];
  var LVL = { "YEŞİL": "GREEN", "SARI": "YELLOW", "KIRMIZI": "RED" };

  var PHRASES = [["BIST 100 (dolar bazında)", "BIST 100 (in dollars)"], ["S&P 500 fonu (SPY)", "S&P 500 fund (SPY)"],
                 ["Nasdaq 100 fonu (QQQ)", "Nasdaq 100 fund (QQQ)"], ["BIST 100 (TL)", "BIST 100 (TRY)"],
                 ["Gram altın", "Gold (gram)"], ["Gram gümüş", "Silver (gram)"], ["Ons altın", "Gold (ounce)"], ["Ons gümüş", "Silver (ounce)"],
                 ["Dolar/TL", "USD/TRY"], ["Brent petrol", "Brent oil"], ["WTI petrol", "WTI oil"],
                 [" oranı:", " ratio:"], [" (başlangıç = 100):", " (start = 100):"], [" (endeks)", " (index)"],
                 ["Endekslenmiş seri olduğu için oranın seviyesi değil, yönü anlamlıdır.", "Rebased series: the ratio's direction matters, not its level."],
                 ["Günlük kapanışlar · son veri ", "Daily closes · latest data "],
                 [" sabahı hazırlandı · Olgusal özet, kendi cümlelerimizle; haberlerin hakları kaynaklarına aittir.",
                  " morning · Factual digest in our own words; news rights belong to their sources."]];
  function phrases(s) {
    for (var i = 0; i < PHRASES.length; i++) if (s.indexOf(PHRASES[i][0]) >= 0) s = s.split(PHRASES[i][0]).join(PHRASES[i][1]);
    return s;
  }
  function fmt(s) {
    s = phrases(s);
    // Turkish percent "−%4,4" / "+%7,9" / "%0,0" -> "−4.4%"; numbers "5.715" / "4,2" -> "5,715" / "4.2"; months
    s = s.replace(/([+−-]?)⁠?%(\d[\d.,]*\d|\d)/g, function (_, sg, n) { return sg + enNum(n) + "%"; });
    s = s.replace(/(^|[^\d.,%])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+,\d+)(?![\d%])/g, function (_, pre, n) { return pre + enNum(n); });
    s = s.replace(MON_RE, function (_, d, m) {
      var i = MON_TR.indexOf(m);
      if (i < 0) i = MON_TR.map(function (x) { return x.slice(0, 3); }).indexOf(m);
      return d + " " + (m.length === 3 ? MON_EN[i].slice(0, 3) : MON_EN[i]);
    });
    return s;
  }
  function tr(raw) {
    var lead = /^\s*/.exec(raw)[0], trail = /\s*$/.exec(raw)[0], s = raw.trim();
    if (!s) return raw;
    if (Object.prototype.hasOwnProperty.call(D, s)) return lead + D[s] + trail;
    if (Object.prototype.hasOwnProperty.call(LVL, s)) return lead + LVL[s] + trail;
    for (var i = 0; i < P.length; i++) {
      var m = P[i][0].exec(s);
      if (m) return lead + fmt(P[i][1](m)) + trail;
    }
    return lead + fmt(s) + trail;
  }

  // add(): page dictionaries (i18n-pages.js) load right after this file, before the body is parsed
  // add(dict, patterns, phrases): patterns = [[RegExp, fn(match)]], phrases = [[tr, en]] (substring swaps)
  function add(o, pats, phr) {
    if (!EN) return;
    if (o) Object.keys(o).forEach(function (k) { if (!Object.prototype.hasOwnProperty.call(D, k)) D[k] = o[k]; });
    (pats || []).forEach(function (x) { P.push(x); });
    (phr || []).forEach(function (x) { PHRASES.push(x); });
  }
  // Long prose pages carry both languages: <div data-lang="tr"> / <div data-lang="en"> (see style.css)
  document.documentElement.setAttribute("data-ui-lang", LANG);
  window.PHD_I18N = Object.freeze({ lang: LANG, en: EN, add: add, t: function (s) { return EN ? tr(String(s)) : String(s); } });
  if (!EN) return;

  var done = new WeakMap();
  var made = new Set();            // strings this script produced: never translate them again (idempotent)
  function once(v) {
    if (made.has(v)) return v;
    var t = tr(v);
    if (made.size > 5000) made.clear();
    made.add(t);
    return t;
  }
  function textNode(n) {
    var p = n.parentNode;
    if (!p || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(p.nodeName)) return;
    if (p.closest && p.closest("[data-noi18n],[data-lang=en]")) return;      // already English
    if (done.get(n) === n.nodeValue) return;
    var t = once(n.nodeValue);
    if (t !== n.nodeValue) n.nodeValue = t;
    done.set(n, n.nodeValue);
  }
  function attrs(e) {
    if (e.closest && e.closest("[data-noi18n]")) return;
    ["aria-label", "title", "placeholder", "alt"].forEach(function (a) {
      var v = e.getAttribute && e.getAttribute(a);
      if (v) { var t = once(v); if (t !== v) e.setAttribute(a, t); }
    });
  }
  function walk(root) {
    if (root.nodeType === 3) { textNode(root); return; }
    if (root.nodeType !== 1) return;
    attrs(root);
    var w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    var n;
    while ((n = w.nextNode())) { if (n.nodeType === 3) textNode(n); else attrs(n); }
  }
  new MutationObserver(function (list) {
    list.forEach(function (r) {
      if (r.type === "characterData") textNode(r.target);
      else if (r.type === "attributes") attrs(r.target);
      else r.addedNodes.forEach(walk);
    });
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true,
                                          attributes: true, attributeFilter: ["aria-label", "title", "placeholder", "alt"] });
  var title = document.querySelector("title");
  if (title) title.textContent = tr(title.textContent.replace(/^(.*) — Piyasa Hava Durumu$/, "$1")) +
    (/ — Piyasa Hava Durumu$/.test(title.textContent) ? " — Piyasa Hava Durumu" : "");
})();

/* Switch link + language-preserving internal links (runs after the DOM is parsed). */
document.addEventListener("DOMContentLoaded", function () {
  "use strict";
  var I = window.PHD_I18N;
  var full = /(^|\/)(index|konum|hareket|karsilastir|hesapla|arsiv|hafta|dunya|yontem)\.html$|\/$/.test(location.pathname) || !/\.html$/.test(location.pathname);
  var nav = document.querySelector("header.masthead nav");
  if (nav) {
    var a = document.createElement("a");
    var u = new URL(location.href);
    u.searchParams.set("lang", I.en ? "tr" : "en");
    a.href = u.pathname + u.search + u.hash;
    a.textContent = I.en ? "TR" : "EN";
    a.className = "lang";
    a.setAttribute("hreflang", I.en ? "tr" : "en");
    a.setAttribute("lang", I.en ? "tr" : "en");
    a.setAttribute("aria-label", I.en ? "Türkçe" : "English");
    nav.appendChild(a);
  }
  if (!I.en) return;
  // bilingual prose pages: #k1 -> #en-k1 when the English block is shown
  if (location.hash && /^#[a-z0-9-]+$/i.test(location.hash)) {
    var tgt = document.getElementById("en-" + location.hash.slice(1));
    if (tgt) setTimeout(function () { tgt.scrollIntoView(); }, 0);
  }
  Array.prototype.forEach.call(document.querySelectorAll("a[href]"), function (x) {
    var h = x.getAttribute("href");
    if (!h || /^(https?:|mailto:|#)/.test(h) || x.classList.contains("lang")) return;
    if (!/(\.html|\/|^\.\/?)(#.*)?$/.test(h) && h !== "./") return;
    var parts = h.split("#");
    x.setAttribute("href", parts[0] + (parts[0].indexOf("?") >= 0 ? "&" : "?") + "lang=en" + (parts[1] ? "#" + parts[1] : ""));
  });
  if (!full) {
    var main = document.querySelector("main");
    if (main) {
      var p = document.createElement("p");
      p.className = "notice";
      p.textContent = /veri\.html$/.test(location.pathname)
        ? "This page is in Turkish; an English summary is at the end (\"In English\")."
        : "This page is available in Turkish only for now. Numbers and dates are shown in English format.";
      main.insertBefore(p, main.firstChild);
    }
  }
});
