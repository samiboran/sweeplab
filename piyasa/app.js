/* Piyasa Hava Durumu — home page. Fetched JSON is treated as data:
   only textContent / DOM APIs, never innerHTML. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  // GitHub Pages preview reads data-feed directly; any other host serves data/site/ next to the page.
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var WORD = { YESIL: "YEŞİL", SARI: "SARI", KIRMIZI: "KIRMIZI" };
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
  }
  function safeLevel(x) { return WORD[x] ? x : null; }

  function render(d) {
    var lvl = safeLevel(d.level);
    var dot = document.querySelector("#headline .dot");
    dot.className = "dot " + (lvl ? "lv-" + lvl.toLowerCase() : "lv-none");
    $("headline-text").textContent = lvl
      ? trDate(d.publish_date) + " — Makro hava: " + WORD[lvl]
      : "Makro hava verisi yok";
    document.title = lvl ? "Makro hava: " + WORD[lvl] + " — Piyasa Hava Durumu" : document.title;

    var mode = d.mode === "live" ? "canlı" : d.mode === "retro" ? "geriye dönük" : "—";
    $("meta").textContent = "Veri: " + trDate(d.data_date) + " kapanışı · Kural sürümü " +
      (d.rules_version || "—") + " · Kayıt: " + mode;

    var n = $("notice");
    if (d.status !== "güncel") {
      n.hidden = false;
      n.textContent = "Güncellenmedi. Gösterilen son iyi veri: " + trDate(d.last_good_date) +
        ". Yeni veri gelene kadar seviye değişmez.";
    } else if (d.level_held && d.held_note) {
      n.hidden = false;
      n.textContent = d.held_note;
    }

    var list = $("rules");
    list.textContent = "";
    (d.rules || []).forEach(function (r) {
      var li = el("li", r.flag === 1 ? "on" : r.flag === 0 ? "off" : "na");
      li.appendChild(el("span", "mark"));
      var body = el("span", "body");
      var a = el("a", "rtitle", r.title);
      a.href = "yontem.html#" + encodeURIComponent(String(r.code || "").toLowerCase());
      body.appendChild(a);
      body.appendChild(el("span", "rgroup", r.group));
      body.appendChild(el("span", "rtext", r.sentence));
      li.appendChild(body);
      li.setAttribute("aria-label", (r.flag === 1 ? "İşaret var: " : r.flag === 0 ? "İşaret yok: " : "Veri yok: ") + r.title);
      list.appendChild(li);
    });

    var det = $("detail-body");
    det.textContent = "";
    var big = el("p", "big", (d.raw_score != null ? d.raw_score : "–") + "/" + (d.max_score || 9));
    det.appendChild(big);
    det.appendChild(el("p", "mute small", "Ham skor. 0–2 YEŞİL, 3–4 SARI, 5 ve üzeri KIRMIZI; seviye ikinci gün onayıyla değişir."));
    var tbl = el("table", "groups");
    var cap = el("caption", "label", "Başlıklara göre");
    tbl.appendChild(cap);
    Object.keys(d.groups || {}).forEach(function (g) {
      var tr = el("tr");
      tr.appendChild(el("th", null, g));
      tr.appendChild(el("td", null, d.groups[g].points + " / " + d.groups[g].max));
      tbl.appendChild(tr);
    });
    det.appendChild(tbl);
    det.appendChild(el("p", "mute small", "Karşılaştırma tarihi: " + trDate(d.compare_date) + " (20 gün önce)."));

    var qs = $("questions");
    qs.textContent = "";
    (d.answers || []).forEach(function (q) {
      var b = el("button", "q", q.q);
      b.type = "button";
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () { ask(q, b); });
      qs.appendChild(b);
    });

    $("foot-meta").textContent = "Veri tarihi " + trDate(d.data_date) + " · Kural sürümü " +
      (d.rules_version || "—") + " · Üretildi " + String(d.generated_at || "—").replace("T", " ").replace("Z", " UTC");
  }

  var timer = null;
  function ask(q, btn) {
    Array.prototype.forEach.call(document.querySelectorAll(".q"), function (b) { b.setAttribute("aria-pressed", "false"); });
    btn.setAttribute("aria-pressed", "true");
    var box = $("answer");
    box.textContent = "";
    box.appendChild(el("p", "aq", q.q));
    var lines = (q.a || []).slice();
    if (timer) clearTimeout(timer);
    (function next() {
      if (!lines.length) {
        if (q.link === "yontem.html") {
          var p = el("p", "line");
          var a = el("a", null, "Yöntem sayfası");
          a.href = "yontem.html";
          p.appendChild(a);
          box.appendChild(p);
        }
        return;
      }
      box.appendChild(el("p", "line", lines.shift()));
      timer = setTimeout(next, reduce ? 0 : 260);
    })();
  }

  function fail() {
    $("headline-text").textContent = "Veri şu an yüklenemedi";
    var n = $("notice");
    n.hidden = false;
    n.textContent = "Günlük veri dosyasına ulaşılamadı. Biraz sonra yeniden deneyin.";
  }

  fetch(DATA + "today.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(fail);
})();
