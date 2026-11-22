/* Piyasa Hava Durumu — level distribution on the method page. Reads data/site/history.csv; DOM APIs only. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var LV = ["YESIL", "SARI", "KIRMIZI"];
  var TR = { YESIL: "YEŞİL", SARI: "SARI", KIRMIZI: "KIRMIZI" }, EN = { YESIL: "GREEN", SARI: "YELLOW", KIRMIZI: "RED" };
  var MTR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var MEN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function fmt(iso, en) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    return m ? (+m[3]) + " " + (en ? MEN : MTR)[+m[2] - 1] + " " + m[1] : "—";
  }
  function count(rows) {
    var c = { YESIL: 0, SARI: 0, KIRMIZI: 0 }, n = 0;
    rows.forEach(function (r) { if (c.hasOwnProperty(r.level)) { c[r.level]++; n++; } });
    return { c: c, n: n };
  }
  function line(k, en) {
    if (!k.n) return en ? "none yet" : "henüz yok";
    return LV.map(function (l) {
      var pct = Math.round(k.c[l] / k.n * 100);
      return (en ? EN[l] : TR[l]) + " " + k.c[l] + (en ? " days (" + pct + "%)" : " gün (%" + pct + ")");
    }).join(", ");
  }
  function render(rows) {
    var retro = count(rows.filter(function (r) { return r.mode !== "live"; }));
    var live = count(rows.filter(function (r) { return r.mode === "live"; }));
    var first = rows.length ? rows[0].date : "";
    var tr = document.getElementById("dagilim"), en = document.getElementById("en-dagilim");
    if (tr) tr.textContent = "Yayımlanan seviyeler (" + fmt(first) + " ile bugün arası) — geriye dönük: " + line(retro) +
      ". Canlı: " + line(live) + ". Kısa bir dönem olduğu için oranlar genellenemez.";
    if (en) en.textContent = "Published levels so far (since " + fmt(first, true) + ") — retrospective: " + line(retro, true) +
      ". Live: " + line(live, true) + ". The period is short, so the shares do not generalise.";
  }
  fetch(DATA + "history.csv", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
    .then(function (t) {
      var lines = t.trim().split(/\r?\n/), head = lines.shift().split(",");
      var iD = head.indexOf("date"), iM = head.indexOf("mode"), iL = head.indexOf("level");
      render(lines.map(function (l) { var c = l.split(","); return { date: c[iD], mode: c[iM], level: c[iL] }; })
        .filter(function (r) { return /^\d{4}-\d{2}-\d{2}$/.test(r.date || ""); }));
    })
    .catch(function () {
      var tr = document.getElementById("dagilim"), en = document.getElementById("en-dagilim");
      if (tr) tr.textContent = "Seviye dağılımı şu an yüklenemedi; günler Arşiv sayfasında.";
      if (en) en.textContent = "The level distribution could not be loaded; see the Archive page.";
    });
})();
