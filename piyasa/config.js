/* Piyasa Hava Durumu — marka ayarları (roadmap S8). Yalnız bu dosyayı düzenleyin.
   Boş bırakılan bağlantılar sayfada gösterilmez. Metinler textContent ile yazılır. */
window.PHD_CONFIG = Object.freeze({
  title: "Piyasa Hava Durumu",
  // Boran (22 Kasım): "İstatistik yalan söylemez" sloganı kaldırıldı (iddialı bulundu). Boşsa gösterilmez.
  tagline: "",
  // Boran (22 Kasım): Altınkulak henüz bitmedi ve sinyalleri doğrulanmadı — bağlantı gizli.
  // Altınkulak doğrulanınca url'yi geri yazın: "https://samiboran.github.io/altinkulak/"
  deeper: { label: "Daha derin araçlar", name: "Altınkulak", url: "" },
  x: "",          // ör. "https://x.com/kullaniciadi" — boşsa gösterilmez
  telegram: "",   // ör. "https://t.me/kanaladi" — herkese açık kanal açılınca (S7)
  // Geri bildirim (Boran, 22 Kasım): site için açılan e-posta adresi. Boşsa bağlantı gösterilmez.
  // Kişisel adres yazmayın — bu adres herkese açık görünür. Bağlantı yalnız mailto: açar; form/izleyici yok.
  feedback: { label: "Öneri ve hata bildir", email: "" },
  // S11: Search Console / Bing doğrulama kodu (yalnız kodun kendisi, ör. "AbC123…"). Deploy sırasında
  // tools/build_static.py ana sayfanın <head> kısmına statik <meta> olarak ekler. Rehber: docs/DEPLOY_PLAN.md
  verification: { google: "", bing: "" }
});

(function () {
  "use strict";
  var C = window.PHD_CONFIG;
  function safeUrl(u) { return typeof u === "string" && /^https:\/\/[^\s"'<>]+$/.test(u); }
  function link(text, url) {
    var a = document.createElement("a");
    a.href = url; a.textContent = text; a.rel = "noopener noreferrer";
    return a;
  }
  function safeEmail(e) { return typeof e === "string" && /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(e); }
  function feedbackLink() {
    var en = /(?:^|[?&])lang=en(?:&|$)/.test(location.search);
    var subject = en ? "Piyasa Hava Durumu — feedback" : "Piyasa Hava Durumu — geri bildirim";
    var body = en
      ? "Page: " + location.pathname + "\n\nSuggestion / bug:\n\n(Please do not share personal financial details.)"
      : "Sayfa: " + location.pathname + "\n\nÖneri / hata:\n\n(Lütfen kişisel finansal bilgi paylaşmayın.)";
    var a = document.createElement("a");
    a.href = "mailto:" + C.feedback.email + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
    a.textContent = C.feedback.label;
    a.className = "feedback";
    return a;
  }
  function apply() {
    document.querySelectorAll("[data-cfg=tagline]").forEach(function (el) { el.textContent = C.tagline; el.hidden = !C.tagline; });
    var foot = document.querySelector("footer");
    if (!foot || foot.querySelector(".brand-links")) return;
    var p = document.createElement("p");
    p.className = "brand-links";
    var parts = [];
    if (safeUrl(C.deeper.url)) {
      var s = document.createElement("span");
      s.textContent = C.deeper.label + ": ";
      s.appendChild(link(C.deeper.name, C.deeper.url));
      parts.push(s);
    }
    if (safeUrl(C.x)) parts.push(link("X", C.x));
    if (safeUrl(C.telegram)) parts.push(link("Telegram", C.telegram));
    if (C.feedback && safeEmail(C.feedback.email)) parts.push(feedbackLink());
    parts.forEach(function (el, i) {
      if (i) p.appendChild(document.createTextNode(" · "));
      p.appendChild(el);
    });
    if (parts.length) foot.insertBefore(p, foot.firstChild);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
})();
