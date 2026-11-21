/* Piyasa Hava Durumu — "Dünyada bu Pazartesi / Cuma". Fetched JSON is data:
   textContent / DOM APIs only; external links get rel="noopener noreferrer". */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
  }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    var a = Math.abs(v).toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (a === "0,0") return "%0,0";
    return (v > 0 ? "+" : "−") + "\u2060%" + a;
  }
  function noLabel(text, label) {
    var t = String(text || ""), p = String(label || "") + ": ";
    return t.indexOf(p) === 0 ? t.slice(p.length) : t;
  }
  function safeUrl(u) { return /^https:\/\//.test(String(u || "")) ? String(u) : null; }
  function srcLink(name, url) {
    var p = el("p", "src");
    p.appendChild(document.createTextNode("Kaynak: "));
    var u = safeUrl(url);
    if (u) {
      var a = el("a", null, name);
      a.href = u; a.rel = "noopener noreferrer"; a.target = "_blank";
      p.appendChild(a);
    } else {
      p.appendChild(document.createTextNode(name));
    }
    return p;
  }

  function yearTable(a) {
    var t = el("table", "yrs"), tb = el("tbody");
    var maxAbs = 0;
    (a.years || []).forEach(function (r) { maxAbs = Math.max(maxAbs, Math.abs(r.chg)); });
    (a.years || []).slice().reverse().forEach(function (r) {
      var tr = el("tr");
      tr.appendChild(el("th", null, r.year));
      var bar = el("td", "bar");
      var b = el("span", r.chg < 0 ? "b neg" : "b");
      b.style.width = (maxAbs ? Math.max(2, Math.round(Math.abs(r.chg) / maxAbs * 100)) : 0) + "%";
      bar.appendChild(b);
      tr.appendChild(bar);
      tr.appendChild(el("td", r.chg < 0 ? "v neg" : "v", pct(r.chg)));
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    return t;
  }

  function render(d) {
    $("h-kicker").textContent = d.edition === "cuma" ? "Cuma baskısı" : "Pazartesi baskısı";
    $("h-title").textContent = d.title || "Dünyada bu hafta";
    document.title = (d.title || "Dünyada bu hafta") + " — Piyasa Hava Durumu";
    $("h-meta").textContent = trDate(d.issue_date) + " · " + (d.week_label || "") + " haftası · son " + (d.years || 10) + " yıl";
    $("h-method").textContent = d.method || "";
    if (d.disclaimer) $("h-disc").textContent = d.disclaimer;
    $("foot-meta").textContent = "Üretildi " + String(d.generated_at || "—").replace("T", " ").replace("Z", " UTC");

    if (d.edition === "cuma") {
      var bu = $("bu"); bu.textContent = "";
      (d.assets || []).forEach(function (a) { if (!a.this_week_sentence) return;
        var p = el("p", "sum");
        p.appendChild(el("strong", null, a.label + ": "));
        p.appendChild(document.createTextNode(noLabel(a.this_week_sentence, a.label)));
        bu.appendChild(p); });
      $("s-bu").hidden = false;
    }

    var g = $("gecmis"); g.textContent = "";
    (d.assets || []).forEach(function (a) {
      var box = el("div", "wk");
      var head = el("div", "wk-head");
      head.appendChild(el("h2", null, a.label));
      if (a.summary) head.appendChild(el("span", "wk-k", a.summary.up + "/" + a.summary.n + " yıl yükseliş"));
      box.appendChild(head);
      box.appendChild(el("p", "wk-s", noLabel(a.sentence, a.label)));
      if (a.years && a.years.length) {
        var det = el("details", "wk-d");
        det.appendChild(el("summary", null, "Yıl yıl"));
        det.appendChild(yearTable(a));
        box.appendChild(det);
      }
      g.appendChild(box);
    });

    if (d.calendar && d.calendar.length) {
      var ul = $("takvim"); ul.textContent = "";
      d.calendar.forEach(function (c) {
        var li = el("li");
        li.appendChild(el("span", "dt", c.day_label));
        li.appendChild(el("span", null, c.name));
        ul.appendChild(li);
      });
      $("s-takvim").hidden = false;
    }

    if (d.tarihte && d.tarihte.length) {
      var t = $("tarih"); t.textContent = "";
      d.tarihte.forEach(function (e) {
        var art = el("article", "th-e");
        art.appendChild(el("p", "th-d", e.day_label + " " + e.year + (e.topic ? " · " + e.topic : "")));
        art.appendChild(el("h3", null, e.title));
        art.appendChild(el("p", null, e.text));
        art.appendChild(srcLink(e.source, e.url));
        t.appendChild(art);
      });
      $("s-tarih").hidden = false;
    }

    if (d.ilk) {
      var i = $("ilk"); i.textContent = "";
      var art2 = el("article", "th-e");
      art2.appendChild(el("p", "th-d", d.ilk.year_label));
      art2.appendChild(el("h3", null, d.ilk.title));
      art2.appendChild(el("p", null, d.ilk.text));
      art2.appendChild(srcLink(d.ilk.source, d.ilk.url));
      i.appendChild(art2);
      $("s-ilk").hidden = false;
    }
  }

  fetch(DATA + "hafta.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(function () { $("h-meta").textContent = "Haftalık baskı henüz yayımlanmadı ya da yüklenemedi."; });
})();
