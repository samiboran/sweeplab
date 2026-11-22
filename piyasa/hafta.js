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

  // English (S13b): use the build's *_en fields; nodes filled with English are marked data-noi18n
  var EN = !!(window.PHD_I18N && window.PHD_I18N.en);
  function pick(tr, en) { return EN && en ? en : tr; }
  function ev(tag, cls, tr, en) {
    var n = el(tag, cls, pick(tr, en));
    if (EN && en) n.setAttribute("data-noi18n", "");
    return n;
  }
  function setT(node, tr, en) {
    node.textContent = pick(tr, en) == null ? "" : String(pick(tr, en));
    if (EN && en) node.setAttribute("data-noi18n", "");
  }

  function render(d) {
    $("h-kicker").textContent = d.edition === "cuma" ? "Cuma baskısı" : "Pazartesi baskısı";
    setT($("h-title"), d.title || "Dünyada bu hafta", d.title_en);
    document.title = pick(d.title || "Dünyada bu hafta", d.title_en) + " — Piyasa Hava Durumu";
    if (EN && d.week_label_en) {
      $("h-meta").textContent = trDate(d.issue_date) + " · week of " + d.week_label_en + " · last " + (d.years || 10) + " years";   // i18n.js converts the Turkish date
    } else {
      $("h-meta").textContent = trDate(d.issue_date) + " · " + (d.week_label || "") + " haftası · son " + (d.years || 10) + " yıl";
    }
    setT($("h-method"), d.method || "", d.method_en);
    if (d.disclaimer) setT($("h-disc"), d.disclaimer, d.disclaimer_en);
    $("foot-meta").textContent = "Üretildi " + String(d.generated_at || "—").replace("T", " ").replace("Z", " UTC");

    if (d.edition === "cuma") {
      var bu = $("bu"); bu.textContent = "";
      (d.assets || []).forEach(function (a) { if (!a.this_week_sentence) return;
        var p = el("p", "sum");
        var lab = pick(a.label, a.label_en), sen = pick(a.this_week_sentence, a.this_week_sentence_en && a.label_en ? a.this_week_sentence_en : null);
        if (EN && a.this_week_sentence_en && a.label_en) p.setAttribute("data-noi18n", "");
        p.appendChild(el("strong", null, (sen === a.this_week_sentence ? a.label : lab) + ": "));
        p.appendChild(document.createTextNode(noLabel(sen, sen === a.this_week_sentence ? a.label : lab)));
        bu.appendChild(p); });
      $("s-bu").hidden = false;
    }

    var g = $("gecmis"); g.textContent = "";
    (d.assets || []).forEach(function (a) {
      var box = el("div", "wk");
      var head = el("div", "wk-head");
      head.appendChild(ev("h2", null, a.label, a.sentence_en ? a.label_en : null));
      if (a.summary) head.appendChild(el("span", "wk-k", a.summary.up + "/" + a.summary.n + " yıl yükseliş"));
      box.appendChild(head);
      box.appendChild(ev("p", "wk-s", noLabel(a.sentence, a.label), a.sentence_en && a.label_en ? noLabel(a.sentence_en, a.label_en) : null));
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
        li.appendChild(ev("span", "dt", c.day_label, c.day_label_en));
        li.appendChild(ev("span", null, c.name, c.name_en));
        ul.appendChild(li);
      });
      $("s-takvim").hidden = false;
    }

    if (d.tarihte && d.tarihte.length) {
      var t = $("tarih"); t.textContent = "";
      d.tarihte.forEach(function (e) {
        var art = el("article", "th-e");
        var en = !!(e.title_en && e.text_en);
        art.appendChild(ev("p", "th-d", e.day_label + " " + e.year + (e.topic ? " · " + e.topic : ""),
          en ? (e.day_label_en || e.day_label) + " " + e.year + (e.topic_en ? " · " + e.topic_en : "") : null));
        art.appendChild(ev("h3", null, e.title, en ? e.title_en : null));
        art.appendChild(ev("p", null, e.text, en ? e.text_en : null));
        art.appendChild(srcLink(e.source, e.url));
        t.appendChild(art);
      });
      $("s-tarih").hidden = false;
    }

    if (d.ilk) {
      var i = $("ilk"); i.textContent = "";
      var art2 = el("article", "th-e");
      var en2 = !!(d.ilk.title_en && d.ilk.text_en);
      art2.appendChild(ev("p", "th-d", d.ilk.year_label, en2 ? d.ilk.year_label_en : null));
      art2.appendChild(ev("h3", null, d.ilk.title, en2 ? d.ilk.title_en : null));
      art2.appendChild(ev("p", null, d.ilk.text, en2 ? d.ilk.text_en : null));
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
