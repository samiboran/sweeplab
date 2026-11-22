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
    "Kontrol: KIRMIZI'ya geçilen günden sonraki 20 gün içinde Nasdaq Bileşik, o günkü kapanışının en az %5 altında kapandıysa \"teyit edildi\", kapanmadıysa \"yanlış alarm\". Seviye KIRMIZI değilken 20 günde %10'luk düşüş olursa \"kaçırılan düşüş\" yazılır. Bu, kuralların ne kadar isabetli olduğunu dürüstçe göstermek içindir; gelecek hakkında bir şey söylemez.":
      "Check: if within 20 days of a switch to RED the Nasdaq Composite closed at least 5% below that day's close, the signal is \"confirmed\"; otherwise it is a \"false alarm\". A 10% drop within 20 days while the level was not RED is listed as a \"missed drop\". This shows honestly how accurate the rules have been; it says nothing about the future.",
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
    "Bu sayfa arşivi JavaScript ile yükler. Ham dosya:": "This page loads the archive with JavaScript. Raw file:"
  });
})();
